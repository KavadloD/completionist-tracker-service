from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.email}>'


class Game(db.Model):
    game_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    platform = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    tags = db.Column(db.String(255))
    run_type = db.Column(db.String(100))
    cover_url = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref='games')
    


class ChecklistItem(db.Model):
    checklist_item_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.game_id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer)

    game = db.relationship('Game', backref='checklist_items')
    
class CommunityChecklist(db.Model):
    community_checklist_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    platform = db.Column(db.String(100))
    genre = db.Column(db.String(100))
    run_type = db.Column(db.String(100))
    tags = db.Column(db.String(255))      

    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    created_by_user = db.relationship('User', backref='community_templates')

def to_dict(self):
    return {
        "game_id": self.game_id,
        "user_id": self.user_id,
        "title": self.title,
        "platform": self.platform,
        "genre": self.genre,
        "tags": self.tags,
        "run_type": self.run_type,
        "progress": getattr(self, "progress", 0),
        "cover_url": self.cover_url,
        "thumbnail_url": self.thumbnail_url or self.cover_url,
    }
