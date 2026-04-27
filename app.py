import os
import json
import random
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, flash, session
)
from models import db, User, Post, Comment, Like, Follow, PointLog, TrendingCache, POINTS_CONFIG
from downloader import (
    download_video, get_video_info, search_videos,
    detect_platform, get_trending_content, generate_auto_caption,
)
from datetime import datetime, timezone

app = Flask(__name__)
app.config["SECRET_KEY"] = "hamzawi-pro-secret-key-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///videopro.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

db.init_app(app)


def get_current_user():
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            return user
    user = User.query.filter_by(username="hamzawi_pro").first()
    if not user:
        user = User(
            username="hamzawi_pro",
            display_name="حمزاوي برو",
            bio="صانر محتوى رقمي 🎬",
            avatar_url="",
            points=250,
        )
        db.session.add(user)
        db.session.commit()
    session["user_id"] = user.id
    return user


def seed_mock_users():
    mock_users = [
        {"username": "hamzawi_pro", "display_name": "حمزاوي برو", "bio": "صانر محتوى رقمي 🎬", "points": 250},
        {"username": "sara_tech", "display_name": "سارة تك", "bio": "مهندسة برمجيات 💻", "points": 180},
        {"username": "ahmed_vlog", "display_name": "أحمد فلوق", "bio": "مدوّن فيديو 📽", "points": 420},
        {"username": "nora_design", "display_name": "نورة ديزاين", "bio": "مصممة جرافيك 🎨", "points": 90},
        {"username": "omar_gaming", "display_name": "عمر قيمنق", "bio": "لاعب محترف 🎮", "points": 800},
    ]
    for mu in mock_users:
        if not User.query.filter_by(username=mu["username"]).first():
            db.session.add(User(**mu))
    db.session.commit()


def seed_demo_posts():
    if Post.query.count() > 0:
        return

    users = User.query.all()
    if not users:
        return

    demo_posts = [
        {
            "title": "أفضل 10 حيل في دالبرمجة",
            "description": "تعرّف على أفضل الحيل البرمجية التي ستوفر وقتك 🚀",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid1/640/360",
            "source_platform": "youtube",
            "duration": "5:30",
            "views_count": 15420,
            "auto_caption": "🎬 أفضل 10 حيل في البرمجة\n👤 بواسطة: حمزاوي برو\n📝 تعرّف على أفضل الحيل البرمجية التي ستوفر وقتك\n⏱️ المدة: 5 دقيقة و 30 ثانية\n👁️ 15.4 ألف مشاهدة\n\n#برمجة #تطوير #تعلم\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "رحلة إلى دبي 🏙️",
            "description": "جولة سياحية في أجمل معالم دبي",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid2/640/360",
            "source_platform": "instagram",
            "duration": "3:15",
            "views_count": 8730,
            "is_watermark_free": True,
            "auto_caption": "🎬 رحلة إلى دبي 🏙️\n👤 بواسطة: سارة تك\n📝 جولة سياحية في أجمل معالم دبي\n⏱️ المدة: 3 دقيقة و 15 ثانية\n\n#دبي #سفر #سياحية\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "وصفة كنافة لذيذة 🍰",
            "description": "طريقة عمل الكنافة بالجبنة خطوة بخطوة",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid3/640/360",
            "source_platform": "tiktok",
            "duration": "1:45",
            "views_count": 52300,
            "is_watermark_free": True,
            "auto_caption": "🎬 وصفة كنافة لذيذة 🍰\n👤 بواسطة: أحمد فلوق\n📝 طريقة عمل الكنافة بالجبنة خطوة بخطوة\n⏱️ المدة: 1 دقيقة و 45 ثانية\n\n#طبخ #كنافة #وصفات\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "تحدي الألعاب الإلكترونية 🎮",
            "description": "تحدي ملحمي مع الأصدقاف في فورتنايت",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid4/640/360",
            "source_platform": "youtube",
            "duration": "12:08",
            "views_count": 34100,
            "auto_caption": "🎬 تحدي الألعاب الإلكترونية 🎮\n👤 بواسطة: عمر قيمنق\n📝 تحدي ملحمي مع الأصدقاف في فورتنايت\n⏱️ المدة: 12 دقيقة و 8 ثانية\n\n#قيمنق #فورتنايت #تحدي\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "تصميم لوغو احترافي ✨",
            "description": "شرح كامل لتصميم شعار من الصفر باستخدام فوتوشوب",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid5/640/360",
            "source_platform": "youtube",
            "duration": "8:22",
            "views_count": 11250,
            "auto_caption": "🎬 تصميم لوغو احترافي ✨\n👤 بواسطة: نورة ديزاين\n📝 شرح كامل لتصميم شعار من الصفر\n⏱️ المدة: 8 دقيقة و 22 ثانية\n\n#تصميم #فوتوشوب #جرافيك\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "رقصة تيك توك الشهيرة 💃",
            "description": "تعلّم الرقصة اللي كل العالم يسويها",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid6/640/360",
            "source_platform": "tiktok",
            "duration": "0:30",
            "views_count": 98700,
            "is_watermark_free": True,
            "auto_caption": "🎬 رقصة تيك توك الشهيرة 💃\n👤 بواسطة: حمزاوي برو\n📝 تعلّم الرقصة اللي كل العالم يسويها\n⏱️ المدة: 30 ثانية\n\n#تيك_توك #رقص #ترند\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "أسرار الذكاء الاصطناعي 🤖",
            "description": "كيف يغير الذكاء الاصطناعي حياتنا اليومية",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid7/640/360",
            "source_platform": "youtube",
            "duration": "15:40",
            "views_count": 67800,
            "auto_caption": "🎬 أسرار الذكاء الاصطناعي 🤖\n📝 كيف يغير الذكاء الاصطناعي حياتنا\n⏱️ المدة: 15 دقيقة و 40 ثانية\n\n#AI #ذكاء_اصطناعي #تقنية\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "مقلب في صديقي 😂",
            "description": "أقوى مقلب سويته في حياتي والنتيجة صادمة",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid8/640/360",
            "source_platform": "instagram",
            "duration": "2:10",
            "views_count": 125000,
            "is_watermark_free": True,
            "auto_caption": "🎬 مقلب في صديقي 😂\n📝 أقوى مقلب سويته في حياتي\n⏱️ المدة: 2 دقيقة و 10 ثانية\n\n#قالب #😂 #كوميديا\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
        {
            "title": "جولة في أكبر مول في العالم 🏬",
            "description": "دبي مول من الداخل - تجربة لا تُنسى",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "thumbnail_url": "https://picsum.photos/seed/vid9/640/360",
            "source_platform": "youtube",
            "duration": "20:15",
            "views_count": 41200,
            "auto_caption": "🎬 جولة في أكبر مول في العالم 🏬\n📝 دبي مول من الداخل - تجربة لا تُنسى\n⏱️ المدة: 20 دقيقة و 15 ثانية\n\n#دبي_مول #تسوق #سفر\n\n📲 تم المشاركة عبر فيديو برو - حمزاوي برو",
        },
    ]

    for i, dp in enumerate(demo_posts):
        user = users[i % len(users)]
        post = Post(user_id=user.id, **dp)
        db.session.add(post)
    db.session.commit()

    posts = Post.query.all()
    for post in posts:
        for u in random.sample(users, min(3, len(users))):
            if not Like.query.filter_by(user_id=u.id, post_id=post.id).first():
                db.session.add(Like(user_id=u.id, post_id=post.id))

    comments_text = [
        "ماشاء الله محتوى رائر! 🔥",
        "استمر يا برل 💪",
        "أفضل فيديو شفته اليوم",
        "شكراً على المشاركة ❤️",
        "محتوى مميز جداً!",
        "يستاهل لايك 👍",
        "اللي يعجبه يضغط لايك ⭐",
        "وش هالجمال! 😍",
        "ياليت تنزل الجزء الثاني",
        "فيديو برو أفضل تطبيق 🏆",
    ]
    for post in posts:
        for j in range(random.randint(1, 4)):
            u = random.choice(users)
            c = Comment(
                user_id=u.id,
                post_id=post.id,
                content=random.choice(comments_text),
            )
            db.session.add(c)

    for u in users:
        for other in users:
            if u.id != other.id and random.random() > 0.4:
                if not Follow.query.filter_by(follower_id=u.id, followed_id=other.id).first():
                    db.session.add(Follow(follower_id=u.id, followed_id=other.id))

    db.session.commit()


# ─── Routes ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    user = get_current_user()
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "trending")
    if sort == "latest":
        posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    else:
        posts = Post.query.order_by(Post.views_count.desc()).paginate(page=page, per_page=12, error_out=False)
    liked_ids = set()
    if user:
        liked_ids = {l.post_id for l in Like.query.filter_by(user_id=user.id).all()}

    trending = get_trending_content()
    top_users = User.query.order_by(User.points.desc()).limit(5).all()

    return render_template(
        "index.html",
        posts=posts,
        user=user,
        liked_ids=liked_ids,
        sort=sort,
        trending=trending,
        top_users=top_users,
    )


@app.route("/download", methods=["GET", "POST"])
def download_page():
    user = get_current_user()
    result = None
    error = None
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        remove_wm = request.form.get("remove_watermark", "on") == "on"
        if not url:
            error = "الرجاء إدخال رابط الفيديو"
        else:
            result = download_video(url, remove_watermark=remove_wm)
            if result and "error" in result:
                error = result["error"]
                result = None
            elif result:
                user.add_points("download")
                db.session.commit()
    return render_template("download.html", user=user, result=result, error=error)


@app.route("/search")
def search_page():
    user = get_current_user()
    query = request.args.get("q", "").strip()
    platform = request.args.get("platform", "youtube")
    results = []
    if query:
        results = search_videos(query, platform=platform)
    return render_template(
        "search.html", user=user, results=results, query=query, platform=platform
    )


@app.route("/post/<int:post_id>")
def view_post(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    post.views_count += 1
    db.session.commit()
    comments = post.comments.order_by(Comment.created_at.desc()).all()
    is_liked = Like.query.filter_by(user_id=user.id, post_id=post.id).first() is not None
    is_following = False
    if user.id != post.user_id:
        is_following = Follow.query.filter_by(follower_id=user.id, followed_id=post.user_id).first() is not None
    return render_template(
        "post.html",
        post=post,
        user=user,
        comments=comments,
        is_liked=is_liked,
        is_following=is_following,
    )


@app.route("/profile/<int:user_id>")
def profile(user_id):
    current_user = get_current_user()
    profile_user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    is_following = False
    if current_user.id != user_id:
        is_following = Follow.query.filter_by(follower_id=current_user.id, followed_id=user_id).first() is not None

    point_history = PointLog.query.filter_by(user_id=user_id).order_by(PointLog.created_at.desc()).limit(20).all()

    return render_template(
        "profile.html",
        profile_user=profile_user,
        user=current_user,
        posts=posts,
        is_following=is_following,
        point_history=point_history,
        points_config=POINTS_CONFIG,
    )


@app.route("/leaderboard")
def leaderboard():
    user = get_current_user()
    users = User.query.order_by(User.points.desc()).all()
    return render_template("leaderboard.html", user=user, users=users)


# ─── API Routes ──────────────────────────────────

@app.route("/api/post", methods=["POST"])
def create_post():
    user = get_current_user()
    data = request.get_json() or request.form
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    video_url = data.get("video_url", "").strip()
    thumbnail_url = data.get("thumbnail_url", "").strip()
    source_platform = data.get("source_platform", "other")
    source_url = data.get("source_url", "")
    duration = data.get("duration", "")
    auto_caption = data.get("auto_caption", "")
    is_watermark_free = data.get("is_watermark_free", False)
    if isinstance(is_watermark_free, str):
        is_watermark_free = is_watermark_free.lower() in ("true", "1", "yes")

    if not title or not video_url:
        return jsonify({"error": "العنوان ورابط الفيديو مطلوبان"}), 400

    post = Post(
        user_id=user.id,
        title=title,
        description=description,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        source_platform=source_platform,
        source_url=source_url,
        duration=duration,
        auto_caption=auto_caption,
        is_watermark_free=is_watermark_free,
    )
    db.session.add(post)
    pts = user.add_points("post_video")
    db.session.commit()
    return jsonify({
        "success": True,
        "post_id": post.id,
        "message": f"تم النشر بنجاح! 🎉 (+{pts} نقطة)",
        "points_earned": pts,
        "total_points": user.points,
    })


@app.route("/api/like/<int:post_id>", methods=["POST"])
def toggle_like(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    existing = Like.query.filter_by(user_id=user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"liked": False, "count": post.likes_count, "points": user.points})
    else:
        db.session.add(Like(user_id=user.id, post_id=post_id))
        pts = user.add_points("like_given")
        if post.user_id != user.id:
            post_author = db.session.get(User, post.user_id)
            if post_author:
                post_author.add_points("like_received")
        db.session.commit()
        return jsonify({
            "liked": True,
            "count": post.likes_count,
            "points_earned": pts,
            "points": user.points,
        })


@app.route("/api/comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    user = get_current_user()
    post = Post.query.get_or_404(post_id)
    data = request.get_json() or request.form
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "التعليق لا يمكن أن يكون فارغاً"}), 400
    comment = Comment(user_id=user.id, post_id=post_id, content=content)
    db.session.add(comment)
    pts = user.add_points("comment_given")
    if post.user_id != user.id:
        post_author = db.session.get(User, post.user_id)
        if post_author:
            post_author.add_points("comment_received")
    db.session.commit()
    return jsonify({
        "success": True,
        "comment": {
            "id": comment.id,
            "content": comment.content,
            "author": user.display_name,
            "author_initial": user.display_name[0],
            "created_at": "الآن",
        },
        "count": post.comments_count,
        "points_earned": pts,
        "points": user.points,
    })


@app.route("/api/follow/<int:user_id>", methods=["POST"])
def toggle_follow(user_id):
    user = get_current_user()
    if user.id == user_id:
        return jsonify({"error": "لا يمكنك متابعة نفسك"}), 400

    target = User.query.get_or_404(user_id)
    existing = Follow.query.filter_by(follower_id=user.id, followed_id=user_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"following": False, "count": target.followers_count, "points": user.points})
    else:
        db.session.add(Follow(follower_id=user.id, followed_id=user_id))
        pts = user.add_points("follow_given")
        target.add_points("follower_received")
        db.session.commit()
        return jsonify({
            "following": True,
            "count": target.followers_count,
            "points_earned": pts,
            "points": user.points,
        })


@app.route("/api/download", methods=["POST"])
def api_download():
    user = get_current_user()
    data = request.get_json()
    url = data.get("url", "").strip() if data else ""
    remove_wm = data.get("remove_watermark", True) if data else True
    if not url:
        return jsonify({"error": "الرجاء إدخال رابط الفيديو"}), 400
    result = download_video(url, remove_watermark=remove_wm)
    if result and "error" in result:
        return jsonify({"error": result["error"]}), 400
    if not result:
        return jsonify({"error": "فشل تحميل الفيديو"}), 500
    pts = user.add_points("download")
    db.session.commit()
    result["points_earned"] = pts
    result["total_points"] = user.points
    return jsonify({"success": True, "data": result})


@app.route("/api/video-info", methods=["POST"])
def api_video_info():
    data = request.get_json()
    url = data.get("url", "").strip() if data else ""
    if not url:
        return jsonify({"error": "الرجاء إدخال رابط الفيديو"}), 400
    info = get_video_info(url)
    if not info:
        return jsonify({"error": "لم يتم العثور على معلومات الفيديو"}), 404
    return jsonify({"success": True, "data": info})


@app.route("/api/generate-caption", methods=["POST"])
def api_generate_caption():
    data = request.get_json()
    title = data.get("title", "") if data else ""
    description = data.get("description", "") if data else ""
    platform = data.get("platform", "youtube") if data else "youtube"
    uploader = data.get("uploader", "") if data else ""
    duration = data.get("duration", "") if data else ""
    tags = data.get("tags", []) if data else []

    info = {
        "title": title,
        "description": description,
        "uploader": uploader,
        "tags": tags,
    }
    if duration:
        parts = duration.split(":")
        if len(parts) == 2:
            info["duration"] = int(parts[0]) * 60 + int(parts[1])

    caption = generate_auto_caption(info)
    return jsonify({"success": True, "caption": caption})


@app.route("/api/trending")
def api_trending():
    trending = get_trending_content()
    return jsonify({"success": True, "data": trending})


@app.route("/api/switch-user/<int:user_id>", methods=["POST"])
def switch_user(user_id):
    user = User.query.get_or_404(user_id)
    session["user_id"] = user.id
    return jsonify({"success": True, "user": {"id": user.id, "display_name": user.display_name}})


# ─── Init ────────────────────────────────

with app.app_context():
    db.drop_all()
    db.create_all()
    seed_mock_users()
    seed_demo_posts()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
