from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

# ─── Points Configuration ────────────────────────────────
POINTS_CONFIG = {
    "post_video": 50,
    "like_given": 5,
    "like_received": 10,
    "comment_given": 15,
    "comment_received": 20,
    "follow_given": 5,
    "follower_received": 25,
    "download": 10,
    "daily_login": 30,
    "share": 10,
}

LEVEL_THRESHOLDS = [
    (0, "مبتدئ", "🌱"),
    (100, "ناشط", "⚡"),
    (300, "محترف", "🔥"),
    (750, "نجم", "⭐"),
    (1500, "أسطورة", "👑"),
    (3000, "حمزاوي ماكس", "💎"),
]


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    avatar_url = db.Column(db.String(500), default="")
    bio = db.Column(db.Text, default="")
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    posts = db.relationship("Post", backref="author", lazy="dynamic")
    comments = db.relationship("Comment", backref="author", lazy="dynamic")
    likes = db.relationship("Like", backref="user", lazy="dynamic")
    point_logs = db.relationship("PointLog", backref="user", lazy="dynamic")

    followers = db.relationship(
        "Follow",
        foreign_keys="Follow.followed_id",
        backref="followed",
        lazy="dynamic",
    )
    following = db.relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        backref="follower",
        lazy="dynamic",
    )

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()

    @property
    def level_info(self):
        current_level = LEVEL_THRESHOLDS[0]
        next_level = LEVEL_THRESHOLDS[1] if len(LEVEL_THRESHOLDS) > 1 else None
        for i, (threshold, name, icon) in enumerate(LEVEL_THRESHOLDS):
            if self.points >= threshold:
                current_level = (threshold, name, icon)
                if i + 1 < len(LEVEL_THRESHOLDS):
                    next_level = LEVEL_THRESHOLDS[i + 1]
                else:
                    next_level = None
        return {
            "name": current_level[1],
            "icon": current_level[2],
            "threshold": current_level[0],
            "next_level": next_level,
        }

    @property
    def level_progress(self):
        info = self.level_info
        if info["next_level"] is None:
            return 100
        current = info["threshold"]
        nxt = info["next_level"][0]
        if nxt == current:
            return 100
        return min(100, int(((self.points - current) / (nxt - current)) * 100))

    def add_points(self, action, amount=None):
        pts = amount if amount is not None else POINTS_CONFIG.get(action, 0)
        if pts <= 0:
            return 0
        self.points += pts
        log = PointLog(user_id=self.id, action=action, points=pts)
        db.session.add(log)
        return pts


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    video_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500), default="")
    source_platform = db.Column(db.String(50), default="unknown")
    source_url = db.Column(db.String(500), default="")
    duration = db.Column(db.String(20), default="")
    views_count = db.Column(db.Integer, default=0)
    auto_caption = db.Column(db.Text, default="")
    is_watermark_free = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    comments = db.relationship(
        "Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan"
    )
    likes = db.relationship(
        "Like", backref="post", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def time_ago(self):
        now = datetime.now(timezone.utc)
        diff = now - self.created_at.replace(tzinfo=timezone.utc)
        seconds = diff.total_seconds()
        if seconds < 60:
            return "الآن"
        elif seconds < 3600:
            m = int(seconds // 60)
            return f"منذ {m} دقيقة" if m > 1 else "منذ دقيقة"
        elif seconds < 86400:
            h = int(seconds // 3600)
            return f"منذ {h} ساعة" if h > 1 else "منذ ساعة"
        else:
            d = int(seconds // 86400)
            return f"منذ {d} يوم" if d > 1 else "منذ يوم"


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("user_id", "post_id"),)


class Follow(db.Model):
    __tablename__ = "follows"
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint("follower_id", "followed_id"),)


class PointLog(db.Model):
    __tablename__ = "point_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class TrendingCache(db.Model):
    __tablename__ = "trending_cache"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    thumbnail_url = db.Column(db.String(500), default="")
    video_url = db.Column(db.String(500), default="")
    platform = db.Column(db.String(50), default="youtube")
    uploader = db.Column(db.String(200), default="")
    view_count = db.Column(db.Integer, default=0)
    duration = db.Column(db.String(20), default="")
    category = db.Column(db.String(50), default="general")
    cached_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
