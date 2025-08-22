from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

db = SQLAlchemy()


# --------- User ---------
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"


# --------- Game ---------
class Game(db.Model):
    game_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)

    title = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    tags = db.Column(db.String(255))
    run_type = db.Column(db.String(100))

    cover_url = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    user = db.relationship("User", backref="games")

    def to_dict(self):
        return {
            "game_id": self.game_id,
            "user_id": self.user_id,
            "title": self.title,
            "platform": self.platform,
            "genre": self.genre,
            "tags": self.tags,
            "run_type": self.run_type,
            "progress": 0,
            "cover_url": self.cover_url,
            "thumbnail_url": self.thumbnail_url or self.cover_url,
        }

    def __repr__(self):
        return f'<Game {self.game_id} "{self.title}">'


# --------- ChecklistItem ---------
class ChecklistItem(db.Model):
    checklist_item_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(
        db.Integer,
        db.ForeignKey("game.game_id", ondelete="CASCADE"),
        nullable=False,
    )
    description = db.Column(db.Text, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer)

    game = db.relationship(
        "Game",
        backref=db.backref("checklist_items", cascade="all, delete-orphan"),
    )

    __table_args__ = (
        UniqueConstraint("game_id", "order", name="uq_checklist_order_per_game"),
    )

    def to_dict(self):
        return {
            "checklist_item_id": self.checklist_item_id,
            "game_id": self.game_id,
            "description": self.description,
            "completed": self.completed,
            "order": self.order,
        }

    def __repr__(self):
        return f"<ChecklistItem {self.checklist_item_id} for game {self.game_id}>"


# --------- CommunityChecklist ---------
class CommunityChecklist(db.Model):
    community_checklist_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    platform = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    run_type = db.Column(db.String(100))
    tags = db.Column(db.String(255))
    thumbnail_url = db.Column(db.Text)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    created_by_user = db.relationship("User", backref="community_templates")

    items = db.relationship(
        "CommunityChecklistItem",
        backref="community_checklist",
        cascade="all, delete-orphan",
        order_by="CommunityChecklistItem.order",
    )

    def to_dict(self, include_items: bool = False):
        base = {
            "community_checklist_id": self.community_checklist_id,
            "title": self.title,
            "description": self.description,
            "platform": self.platform,
            "genre": self.genre,
            "run_type": self.run_type,
            "tags": self.tags,
            "thumbnail_url": self.thumbnail_url,
            "created_by_user_id": self.created_by_user_id,
            "created_by_username": self.created_by_user.username
            if self.created_by_user
            else None,
        }
        if include_items:
            base["items"] = [i.to_dict() for i in self.items]
        return base


# --------- CommunityChecklistItem ---------
class CommunityChecklistItem(db.Model):
    community_item_id = db.Column(db.Integer, primary_key=True)
    community_checklist_id = db.Column(
        db.Integer,
        db.ForeignKey("community_checklist.community_checklist_id", ondelete="CASCADE"),
        nullable=False,
    )
    description = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("community_checklist_id", "order", name="uq_comm_item_order"),
    )

    def to_dict(self):
        return {
            "community_item_id": self.community_item_id,
            "community_checklist_id": self.community_checklist_id,
            "description": self.description,
            "order": self.order,
        }
