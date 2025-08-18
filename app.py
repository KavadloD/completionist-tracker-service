import os
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import func

from models import db, Game, ChecklistItem
from users import register_user, login_user
from checklist import (
    add_checklist_item,
    get_checklist,
    update_checklist_item,
    delete_checklist_item,
)
from models import CommunityChecklist
from werkzeug.security import generate_password_hash

# App factory-style setup kept simple in a single file
app = Flask(__name__)

# CORS: enable credentials if you use cookies or auth headers from the browser
allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

#password is postgres123
#port 5432

db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost/completionist_db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Bind SQLAlchemy
db.init_app(app)

migrate = Migrate(app, db)


# --------- Health check ---------
@app.route("/api/test")
def test():
    return jsonify({"message": "API is working"})


# --------- Auth ---------
@app.route("/api/register", methods=["POST"])
def register():
    return register_user()


@app.route("/api/login", methods=["POST"])
def login():
    return login_user()


@app.route('/api/seed-community')
def seed_community():
    from models import User, db, CommunityChecklist
    from werkzeug.security import generate_password_hash

    # Check if user already exists
    existing_user = User.query.filter_by(email="seed@example.com").first()

    if not existing_user:
        hashed_pw = generate_password_hash("test123")
        user = User(username="seed_user", email="seed@example.com", password_hash=hashed_pw)
        db.session.add(user)
        db.session.commit()
    else:
        user = existing_user

    # Now create checklists linked to that user
    sample_data = [
        CommunityChecklist(
            title="Hollow Knight – 100% Completion",
            description="All charms, grubs, bosses, and true ending.",
            platform="PC",
            genre="Metroidvania",
            created_by_user_id=user.user_id,
        ),
        CommunityChecklist(
            title="Final Fantasy X – Aeons and Side Quests",
            description="Capture monsters, get all celestial weapons, finish all side quests.",
            platform="PlayStation",
            genre="RPG",
            created_by_user_id=user.user_id,
        ),
        CommunityChecklist(
            title="Metroid Prime – Minimal Item Run",
            description="No energy tanks, no missiles, hard mode speedrun.",
            platform="GameCube",
            genre="Action-Adventure",
            created_by_user_id=user.user_id,
        ),
    ]

    db.session.bulk_save_objects(sample_data)
    db.session.commit()

    return {'message': 'Community checklist seeded'}


# --------- Checklist ---------
@app.route("/api/games/<int:game_id>/checklist", methods=["GET"])
def fetch_checklist(game_id):
    return get_checklist(game_id)


@app.route("/api/games/<int:game_id>/checklist", methods=["POST"])
def create_checklist_item(game_id):
    return add_checklist_item(game_id)


@app.route("/api/checklist/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    return update_checklist_item(item_id)


@app.route("/api/checklist/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    return delete_checklist_item(item_id)


# --------- Games ---------
@app.route('/api/games', methods=['POST'])
def add_game():
    data = request.get_json()
    game = Game(
        user_id=data['user_id'],
        title=data['title'],
        platform=data['platform'],
        genre=data['genre'],
        run_type=data.get('run_type'),
        tags=data.get('tags')
    )
    db.session.add(game)
    db.session.commit()
    return jsonify({'message': 'Game added!'}), 201


@app.route("/api/games/<int:game_id>", methods=["GET"])
def get_game(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"message": "Game not found"}), 404

    return jsonify(
        {
            "game_id": game.game_id,
            "user_id": game.user_id,
            "title": game.title,
            "platform": game.platform,
            "genre": game.genre,
        }
    )

@app.route('/api/games/<int:game_id>', methods=['PATCH', 'PUT'])
def update_game(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({'message': 'Game not found'}), 404

    data = request.get_json(silent=True) or {}
    changed = False

    if 'title' in data:
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'message': 'title cannot be empty'}), 400
        game.title = title
        changed = True

    if 'platform' in data:
        platform = (data.get('platform') or '').strip()
        game.platform = platform or None
        changed = True

    if 'genre' in data:
        genre = (data.get('genre') or '').strip()
        game.genre = genre or None
        changed = True

    if not changed:
        return jsonify({'message': 'no changes provided'}), 400

    db.session.commit()
    return jsonify({
        'game_id': game.game_id,
        'user_id': game.user_id,
        'title': game.title,
        'platform': game.platform,
        'genre': game.genre
    }), 200



@app.route("/api/games/<int:game_id>", methods=["DELETE"])
def delete_game(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"message": "Game not found"}), 404

    db.session.query(ChecklistItem).filter_by(game_id=game_id).delete(
        synchronize_session=False
    )

    db.session.delete(game)
    db.session.commit()
    return jsonify({"message": "Game deleted"}), 200


@app.route("/api/games", methods=["GET"])
def list_games():
    user_id = request.args.get("user_id", type=int)

    query = db.session.query(Game)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    games = query.all()

    return jsonify(
        [
            {
                "game_id": g.game_id,
                "user_id": g.user_id,
                "title": g.title,
                "platform": g.platform,
                "genre": g.genre,
            }
            for g in games
        ]
    )


@app.route("/api/games/<int:game_id>/progress", methods=["GET"])
def game_progress(game_id):
    # Ensure game exists
    if not db.session.get(Game, game_id):
        return jsonify({"message": "Game not found"}), 404

    total = (
        db.session.query(func.count(ChecklistItem.checklist_item_id))
        .filter_by(game_id=game_id)
        .scalar()
    )
    done = (
        db.session.query(func.count(ChecklistItem.checklist_item_id))
        .filter_by(game_id=game_id, completed=True)
        .scalar()
    )

    total = int(total or 0)
    done = int(done or 0)
    pct = 0 if total == 0 else round((done / total) * 100)

    return jsonify({"game_id": game_id, "completed": done, "total": total, "percent": pct})

# --------- Community ---------
@app.route("/api/community", methods=["GET"])
def list_community_checklists():
    templates = CommunityChecklist.query.all()

    return jsonify([
        {
            "community_checklist_id": t.community_checklist_id,
            "title": t.title,
            "description": t.description,
            "platform": t.platform,
            "genre": t.genre
        }
        for t in templates
    ])

@app.route("/api/community/import/<int:template_id>", methods=["POST"])
def import_community_checklist(template_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"message": "Missing user_id"}), 400

    template = db.session.get(CommunityChecklist, template_id)
    if not template:
        return jsonify({"message": "Template not found"}), 404

    # Create new Game entry
    new_game = Game(
        user_id=user_id,
        title=template.title,
        platform=template.platform,
        genre=template.genre
    )
    db.session.add(new_game)
    db.session.commit()

    return jsonify({
        "message": "Checklist imported",
        "new_game_id": new_game.game_id
    }), 201

# --------- Error Handlers ---------
@app.errorhandler(404)
def not_found(_):
    return jsonify({"message": "Not found"}), 404


@app.errorhandler(400)
def bad_request(_):
    return jsonify({"message": "Bad request"}), 400


@app.errorhandler(500)
def internal_error(_):
    # Avoid leaking stack traces to clients
    return jsonify({"message": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
