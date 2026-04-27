import os
import re
import json
import yt_dlp
import logging
import hashlib

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "static", "videos")
THUMBNAIL_DIR = os.path.join(BASE_DIR, "static", "thumbnails")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


def detect_platform(url):
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    elif "x.com" in url_lower or "twitter.com" in url_lower:
        return "x"
    return "other"


def _get_watermark_free_opts(platform, base_opts):
    """
    Configure yt-dlp options to bypass/remove watermarks for TikTok and Instagram.
    - TikTok: uses the API endpoint that serves watermark-free versions
    - Instagram: fetches original quality which doesn't contain overlay watermarks
    """
    if platform == "tiktok":
        base_opts.update({
            "format": "best",
            "extractor_args": {"tiktok": {"api_hostname": "api22-normal-c-useast2a.tiktokv.com"}},
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        })
    elif platform == "instagram":
        base_opts.update({
            "format": "best",
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                ),
            },
        })
    return base_opts


def generate_auto_caption(info):
    """
    Generate an automatic Arabic caption/description for a video based on its metadata.
    Uses title, tags, description, uploader, and duration to create a social-ready caption.
    """
    title = info.get("title", "") or ""
    description = info.get("description", "") or ""
    uploader = info.get("uploader", "") or info.get("channel", "") or ""
    tags = info.get("tags", []) or []
    duration = info.get("duration", 0) or 0
    categories = info.get("categories", []) or []
    view_count = info.get("view_count", 0) or 0

    caption_parts = []

    # Main title line
    if title:
        caption_parts.append(f"🎬 {title}")

    # Creator attribution
    if uploader:
        caption_parts.append(f"👤 بواسطة: {uploader}")

    # Smart description extraction — first meaningful sentence
    if description:
        lines = [l.strip() for l in description.split("\n") if l.strip()]
        meaningful = [l for l in lines if len(l) > 10 and not l.startswith("http")]
        if meaningful:
            desc_line = meaningful[0]
            if len(desc_line) > 150:
                desc_line = desc_line[:147] + "..."
            caption_parts.append(f"📝 {desc_line}")

    # Duration info
    if duration > 0:
        mins = int(duration // 60)
        secs = int(duration % 60)
        if mins > 0:
            caption_parts.append(f"⏱️ المدة: {mins} دقيقة و {secs} ثانية")
        else:
            caption_parts.append(f"⏱️ المدة: {secs} ثانية")

    # View count
    if view_count > 0:
        if view_count >= 1_000_000:
            caption_parts.append(f"👁️ {view_count / 1_000_000:.1f} مليون مشاهدة")
        elif view_count >= 1_000:
            caption_parts.append(f"👁️ {view_count / 1_000:.1f} ألف مشاهدة")
        else:
            caption_parts.append(f"👁️ {view_count:,} مشاهدة")

    # Hashtags from tags
    if tags:
        selected_tags = tags[:5]
        hashtags = " ".join(f"#{t.replace(' ', '_')}" for t in selected_tags)
        caption_parts.append(f"\n{hashtags}")

    # Category badges
    if categories:
        cat_map = {
            "Music": "🎵 موسيقى",
            "Gaming": "🎮 ألعاب",
            "Sports": "⚽ رياضة",
            "Education": "📚 تعليم",
            "Entertainment": "🎭 ترفيه",
            "Science & Technology": "🔬 تقنية",
            "News & Politics": "📰 أخبار",
            "Film & Animation": "🎬 أفلام",
            "Comedy": "😂 كوميديا",
            "Howto & Style": "✨ نصائح",
            "People & Blogs": "📝 مدونات",
        }
        for cat in categories:
            if cat in cat_map:
                caption_parts.append(cat_map[cat])
                break

    caption_parts.append("\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو")

    return "\n".join(caption_parts)


def get_video_info(url):
    """Extract video metadata without downloading."""
    platform = detect_platform(url)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "no_color": True,
    }
    ydl_opts = _get_watermark_free_opts(platform, ydl_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return None
            duration_secs = info.get("duration", 0) or 0
            mins = int(duration_secs // 60)
            secs = int(duration_secs % 60)
            duration_str = f"{mins}:{secs:02d}"

            auto_caption = generate_auto_caption(info)

            return {
                "title": info.get("title", "بدون عنوان"),
                "description": info.get("description", ""),
                "thumbnail": info.get("thumbnail", ""),
                "duration": duration_str,
                "uploader": info.get("uploader", "غير معروف"),
                "view_count": info.get("view_count", 0),
                "platform": platform,
                "url": url,
                "webpage_url": info.get("webpage_url", url),
                "id": info.get("id", ""),
                "auto_caption": auto_caption,
                "is_watermark_free": platform in ("tiktok", "instagram"),
            }
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None


def download_video(url, filename=None, remove_watermark=True):
    """Download video with optional watermark removal for TikTok/Instagram."""
    platform = detect_platform(url)
    if not filename:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"video_{platform}_{url_hash}"

    output_path = os.path.join(DOWNLOAD_DIR, f"{filename}.%(ext)s")

    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "writethumbnail": True,
        "merge_output_format": "mp4",
        "postprocessors": [],
    }

    is_watermark_free = False
    if remove_watermark and platform in ("tiktok", "instagram"):
        ydl_opts = _get_watermark_free_opts(platform, ydl_opts)
        is_watermark_free = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return None

            downloaded_file = None
            for ext in ["mp4", "webm", "mkv"]:
                candidate = os.path.join(DOWNLOAD_DIR, f"{filename}.{ext}")
                if os.path.exists(candidate):
                    downloaded_file = candidate
                    break

            if not downloaded_file:
                for f in os.listdir(DOWNLOAD_DIR):
                    if f.startswith(filename):
                        downloaded_file = os.path.join(DOWNLOAD_DIR, f)
                        break

            if not downloaded_file:
                return None

            thumb_path = ""
            for ext in ["jpg", "png", "webp"]:
                candidate = os.path.join(DOWNLOAD_DIR, f"{filename}.{ext}")
                if os.path.exists(candidate):
                    thumb_path = candidate
                    break

            duration_secs = info.get("duration", 0) or 0
            mins = int(duration_secs // 60)
            secs = int(duration_secs % 60)

            auto_caption = generate_auto_caption(info)

            return {
                "title": info.get("title", "بدون عنوان"),
                "description": info.get("description", ""),
                "video_path": os.path.basename(downloaded_file),
                "thumbnail_path": os.path.basename(thumb_path) if thumb_path else "",
                "thumbnail_url": info.get("thumbnail", ""),
                "duration": f"{mins}:{secs:02d}",
                "platform": platform,
                "source_url": url,
                "auto_caption": auto_caption,
                "is_watermark_free": is_watermark_free,
            }
    except Exception as e:
        logger.error(f"Download error: {e}")
        return {"error": str(e)}


def search_videos(query, platform="youtube", max_results=12):
    """Search for videos using yt-dlp's search feature."""
    search_queries = {
        "youtube": f"ytsearch{max_results}:{query}",
        "instagram": f"ytsearch{max_results}:{query} instagram reel",
        "tiktok": f"ytsearch{max_results}:{query} tiktok",
        "x": f"ytsearch{max_results}:{query} twitter video",
    }

    search_url = search_queries.get(platform, f"ytsearch{max_results}:{query}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "no_color": True,
        "extract_flat": False,
    }

    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get("entries", []) if info else []
            for entry in entries:
                if entry is None:
                    continue
                dur = entry.get("duration", 0) or 0
                mins = int(dur // 60)
                secs = int(dur % 60)
                results.append({
                    "title": entry.get("title", "بدون عنوان"),
                    "thumbnail": entry.get("thumbnail", ""),
                    "duration": f"{mins}:{secs:02d}",
                    "uploader": entry.get("uploader", "غير معروف"),
                    "view_count": entry.get("view_count", 0),
                    "url": entry.get("webpage_url", entry.get("url", "")),
                    "platform": platform,
                    "id": entry.get("id", ""),
                })
    except Exception as e:
        logger.error(f"Search error: {e}")

    return results


def get_trending_content():
    """
    Fetch trending/viral content from platforms.
    Returns mock trending data structured like real API responses.
    In production, this would use official APIs (YouTube Data API, etc).
    """
    trending_data = [
        {
            "title": "أغنية عربية تكسر الإنترنت 🎵",
            "thumbnail_url": "https://picsum.photos/seed/trend1/640/360",
            "video_url": "https://www.youtube.com/watch?v=trending1",
            "platform": "youtube",
            "uploader": "أصالة نصري",
            "view_count": 45_000_000,
            "duration": "4:32",
            "category": "music",
        },
        {
            "title": "تحدي الطبخ العربي 🔥",
            "thumbnail_url": "https://picsum.photos/seed/trend2/640/360",
            "video_url": "https://www.youtube.com/watch?v=trending2",
            "platform": "tiktok",
            "uploader": "شيف عمر",
            "view_count": 12_800_000,
            "duration": "0:58",
            "category": "food",
        },
        {
            "title": "ردة فعل على مباراة الكلاسيكو ⚽",
            "thumbnail_url": "https://picsum.photos/seed/trend3/640/360",
            "video_url": "https://www.youtube.com/watch?v=trending3",
            "platform": "youtube",
            "uploader": "عبدالرزاق حمدالله",
            "view_count": 8_500_000,
            "duration": "12:45",
            "category": "sports",
        },
        {
            "title": "رقصة فيروسية جديدة 💃",
            "thumbnail_url": "https://picsum.photos/seed/trend4/640/360",
            "video_url": "https://www.tiktok.com/trending4",
            "platform": "tiktok",
            "uploader": "نور ستارز",
            "view_count": 32_000_000,
            "duration": "0:22",
            "category": "entertainment",
        },
        {
            "title": "مراجعة آيفون 17 الجديد 📱",
            "thumbnail_url": "https://picsum.photos/seed/trend5/640/360",
            "video_url": "https://www.youtube.com/watch?v=trending5",
            "platform": "youtube",
            "uploader": "أبو فلة",
            "view_count": 6_200_000,
            "duration": "18:30",
            "category": "tech",
        },
        {
            "title": "فلوق السفر إلى اليابان 🇯🇵",
            "thumbnail_url": "https://picsum.photos/seed/trend6/640/360",
            "video_url": "https://www.youtube.com/watch?v=trending6",
            "platform": "instagram",
            "uploader": "ديمة بشار",
            "view_count": 4_100_000,
            "duration": "6:15",
            "category": "travel",
        },
        {
            "title": "تعلم البرمجة في 10 دقائق 💻",
            "thumbnail_url": "https://picsum.photos/seed/trend7/640/360",
            "video_url": "https://www.youtube.com/watch?v=trending7",
            "platform": "youtube",
            "uploader": "إلياس تك",
            "view_count": 2_900_000,
            "duration": "10:05",
            "category": "education",
        },
        {
0623خبار عاجلة: إطلاق مشروع نيوم 🏗️",
            "thumbnail_url": "https://picsum.photos/seed/trend8/640/360",
            "video_url": "https://x.com/trending8",
            "platform": "x",
            "uploader": "العربية",
            "view_count": 15_700_000,
            "duration": "2:30",
            "category": "news",
        },
        {
            "title": "كوميديا سعودية مضحكة 😂",
            "thumbnail_url": "https://picsum.photos/seed/trend9/640/360",
            "video_url": "https://www.tiktok.com/trending9",
            "platform": "tiktok",
            "uploader": "فيصل العبدالله",
            "view_count": 9_400_000,
            "duration": "0:45",
            "category": "comedy",
        },
        {
            "title": "تمارين رياضية منزلية 💪",
            "thumbnail_url": "https://picsum.photos/seed/trend10/640/360",
            "video_url": "https://www.instagram.com/trending10",
            "platform": "instagram",
            "uploader": "فيتنس عرب",
            "view_count": 3_600_000,
            "duration": "8:20",
            "category": "fitness",
        },
    ]
    return trending_data
