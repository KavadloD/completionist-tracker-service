import os
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import func

from models import db, Game, ChecklistItem, CommunityChecklist, CommunityChecklistItem
from users import register_user, login_user
from checklist import (
    add_checklist_item,
    get_checklist,
    update_checklist_item,
    delete_checklist_item,
)
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from flask_cors import cross_origin

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



#TEMP
@app.post("/_admin/repair_community")
def _admin_repair_community():
    # lock it down with a token
    token = request.args.get("k") or request.headers.get("X-Admin-Token")
    if not token or token != os.environ.get("ADMIN_REPAIR_TOKEN"):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    actions = []

    def col_exists(table, col):
        q = text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name=:t AND column_name=:c
            LIMIT 1
        """)
        return db.session.execute(q, {"t": table, "c": col}).scalar() is not None

    def table_exists(table):
        q = text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name=:t
            LIMIT 1
        """)
        return db.session.execute(q, {"t": table}).scalar() is not None

    def constraint_exists(table, name):
        q = text("""
            SELECT 1
            FROM pg_constraint
            WHERE conname = :n
            LIMIT 1
        """)
        return db.session.execute(q, {"n": name}).scalar() is not None

    # 1) community_checklist.thumbnail_url
    if not col_exists("community_checklist", "thumbnail_url"):
        db.session.execute(text("ALTER TABLE community_checklist ADD COLUMN thumbnail_url TEXT"))
        actions.append("add community_checklist.thumbnail_url")

    # 2) community_checklist_item table
    if not table_exists("community_checklist_item"):
        db.session.execute(text("""
            CREATE TABLE community_checklist_item (
              community_item_id SERIAL PRIMARY KEY,
              community_checklist_id INTEGER NOT NULL REFERENCES community_checklist(community_checklist_id) ON DELETE CASCADE,
              description TEXT NOT NULL,
              "order" INTEGER
            )
        """))
        actions.append("create community_checklist_item")

    # 3) unique (community_checklist_id, order)
    if not constraint_exists("community_checklist_item", "uq_comm_item_order"):
        db.session.execute(text("""
            ALTER TABLE community_checklist_item
            ADD CONSTRAINT uq_comm_item_order UNIQUE (community_checklist_id, "order")
        """))
        actions.append("add uq_comm_item_order")

    # 4) checklist_item.completed -> NOT NULL default false (idempotent)
    if col_exists("checklist_item", "completed"):
        # backfill nulls
        db.session.execute(text("UPDATE checklist_item SET completed = FALSE WHERE completed IS NULL"))
        # set default false (ignore if already set)
        try:
            db.session.execute(text("ALTER TABLE checklist_item ALTER COLUMN completed SET DEFAULT FALSE"))
            actions.append("set default on checklist_item.completed")
        except Exception:
            pass
        # enforce not null (ignore if already not null)
        try:
            db.session.execute(text("ALTER TABLE checklist_item ALTER COLUMN completed SET NOT NULL"))
            actions.append("set NOT NULL on checklist_item.completed")
        except Exception:
            pass

    # 5) game extra columns (add if missing)
    if not col_exists("game", "cover_url"):
        db.session.execute(text("ALTER TABLE game ADD COLUMN cover_url TEXT"))
        actions.append("add game.cover_url")
    if not col_exists("game", "thumbnail_url"):
        db.session.execute(text("ALTER TABLE game ADD COLUMN thumbnail_url TEXT"))
        actions.append("add game.thumbnail_url")
    if not col_exists("game", "created_at"):
        db.session.execute(text("ALTER TABLE game ADD COLUMN created_at TIMESTAMPTZ DEFAULT now()"))
        actions.append("add game.created_at")
    if not col_exists("game", "updated_at"):
        db.session.execute(text("ALTER TABLE game ADD COLUMN updated_at TIMESTAMPTZ DEFAULT now()"))
        actions.append("add game.updated_at")

    # 6) stamp alembic to latest (your new revision)
    target_rev = "745f8c5ac33d"  # community_add_thumbnail_url_community_...
    # ensure alembic_version table exists
    db.session.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
    current = db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    if current is None:
        db.session.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": target_rev})
    else:
        db.session.execute(text("UPDATE alembic_version SET version_num=:v"), {"v": target_rev})
    actions.append(f"stamp alembic to {target_rev}")

    db.session.commit()
    return jsonify({"ok": True, "actions": actions})
# --- END TEMP ROUTE ---

@app.route("/admin/fix-schema")
@cross_origin()
def fix_schema():
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE game ADD COLUMN IF NOT EXISTS cover_url TEXT"))
        return {"message": "Schema fixed (cover_url ensured)"}
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/api/fix_cover_url", methods=["POST"])
def fix_cover_url():
    try:
        with db.engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE game ADD COLUMN IF NOT EXISTS cover_url TEXT")
            )
            conn.commit()
        return {"message": "Schema fixed (cover_url ensured)"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/games/<int:game_id>/thumbnail", methods=["PATCH"])
def update_game_thumbnail(game_id):
    from urllib.parse import urlparse
    game = Game.query.get_or_404(game_id)

    data = request.get_json(silent=True) or {}
    url = data.get("thumbnail_url")
    if not url:
        return jsonify({"error": "thumbnail_url is required"}), 400

    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return jsonify({"error": "thumbnail_url must be a valid http(s) URL"}), 400

    game.thumbnail_url = url
    db.session.commit()
    return jsonify({
        "message": "Thumbnail updated",
        "game_id": game.game_id,
        "thumbnail_url": game.thumbnail_url
    }), 200

@app.route("/api/admin/thumbnail-column/check", methods=["GET"])
def check_thumbnail_column():
    try:
        exists = db.session.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'game' AND column_name = 'thumbnail_url'
        """)).scalar() is not None
        return jsonify({"thumbnail_column_exists": exists}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/thumbnail-column/fix", methods=["POST"])
def fix_thumbnail_column():
    try:
        db.session.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS thumbnail_url TEXT"))
        db.session.commit()
        return jsonify({"message": "thumbnail_url column ensured"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/games/<int:game_id>/thumbnail", methods=["GET"])
def get_game_thumbnail(game_id):
    game = Game.query.get_or_404(game_id)
    return jsonify({
        "game_id": game.game_id,
        "thumbnail_url": game.thumbnail_url,
        "cover_url": game.cover_url  # fallback
    }), 200

@app.route("/api/games/thumbnails", methods=["GET"])
def list_game_thumbnails():
    user_id = request.args.get("user_id", type=int)
    q = Game.query
    if user_id:
        q = q.filter_by(user_id=user_id)

    rows = (
        q.with_entities(Game.game_id, Game.thumbnail_url, Game.cover_url)
         .order_by(Game.game_id.desc())
         .all()
    )

    data = [
        {
            "game_id": gid,
            "thumbnail_url": thumb or cover,
            "cover_url": cover
        }
        for gid, thumb, cover in rows
    ]
    return jsonify(data), 200

@app.route("/api/games/with-thumbnails", methods=["GET"])
def list_games_with_thumbnails():
    user_id = request.args.get("user_id", type=int)

    q = db.session.query(Game)
    if user_id is not None:
        q = q.filter_by(user_id=user_id)

    games = q.all()
    return jsonify([
        {
            "game_id": g.game_id,
            "user_id": g.user_id,
            "title": g.title,
            "platform": g.platform,
            "genre": g.genre,
            "run_type": g.run_type,
            "tags": g.tags,
            "cover_url": g.cover_url,
            "thumbnail_url": getattr(g, "thumbnail_url", None) or g.cover_url
        }
        for g in games
    ]), 200

@app.route("/api/admin/thumbnails/backfill", methods=["POST"])
def backfill_thumbnails():
    data = request.get_json(silent=True) or {}
    default_url = data.get("default_url")  # used if both thumbnail and cover are empty
    user_id = request.args.get("user_id", type=int)

    q = Game.query
    if user_id is not None:
        q = q.filter(Game.user_id == user_id)

    updated = 0
    games = q.all()
    for g in games:
        if not getattr(g, "thumbnail_url", None):
            # prefer cover_url if present otherwise use provided default
            if getattr(g, "cover_url", None):
                g.thumbnail_url = g.cover_url
                updated += 1
            elif default_url:
                g.thumbnail_url = default_url
                updated += 1

    db.session.commit()
    return jsonify({"updated": updated}), 200


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

    # Create checklists linked to that user
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
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    user_id = data.get('user_id')

    if not user_id or not title:
        return jsonify({"message": "user_id and non-empty title are required"}), 400

    game = Game(
        user_id=user_id,
        title=title,
        platform=(data.get('platform') or '').strip() or None,
        genre=(data.get('genre') or '').strip() or None,
        run_type=(data.get('run_type') or '').strip() or None,
        tags=(data.get('tags') or '').strip() or None,
        cover_url=(data.get('cover_url') or '').strip() or None,
        thumbnail_url=(data.get('thumbnail_url') or '').strip() or None,
    )
    db.session.add(game)
    db.session.commit()
    return jsonify({'message': 'Game added!', 'game_id': game.game_id}), 201



@app.route("/api/games/<int:game_id>", methods=["GET"])
def get_game(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"message": "Game not found"}), 404
    return jsonify(game.to_dict()), 200

# GET many
@app.route("/api/games", methods=["GET"])
def list_games():
    user_id = request.args.get("user_id", type=int)
    q = db.session.query(Game)
    if user_id is not None:
        q = q.filter_by(user_id=user_id)
    rows = q.order_by(Game.game_id.desc()).all()
    return jsonify([g.to_dict() for g in rows]), 200


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
        game.platform = (data.get('platform') or '').strip() or None
        changed = True

    if 'genre' in data:
        game.genre = (data.get('genre') or '').strip() or None
        changed = True

    if 'run_type' in data:
        game.run_type = (data.get('run_type') or '').strip() or None
        changed = True

    if 'tags' in data:
        game.tags = (data.get('tags') or '').strip() or None
        changed = True

    if not changed:
        return jsonify({'message': 'no changes provided'}), 400

    db.session.commit()
    return jsonify({
        'game_id': game.game_id,
        'user_id': game.user_id,
        'title': game.title,
        'platform': game.platform,
        'genre': game.genre,
        'run_type': game.run_type,
        'tags': game.tags
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



@app.route("/api/games/<int:game_id>/progress", methods=["GET"])
def game_progress(game_id):
    if not db.session.get(Game, game_id):
        return jsonify({"message": "Game not found"}), 404

    total = db.session.query(func.count(ChecklistItem.checklist_item_id)).filter_by(game_id=game_id).scalar()
    done = db.session.query(func.count(ChecklistItem.checklist_item_id)).filter_by(game_id=game_id, completed=True).scalar()

    total = int(total or 0)
    done = int(done or 0)
    pct = 0 if total == 0 else round((done / total) * 100)

    return jsonify({"game_id": game_id, "completed": done, "total": total, "percent": pct})

# --------- Community ---------
@app.route("/api/community", methods=["GET"])
def list_community_checklists():
    templates = CommunityChecklist.query.order_by(CommunityChecklist.community_checklist_id.desc()).all()
    return jsonify([
        {
            "community_checklist_id": t.community_checklist_id,
            "title": t.title,
            "description": t.description,
            "platform": t.platform,
            "genre": t.genre,
            "run_type": t.run_type,
            "tags": t.tags,
            "thumbnail_url": t.thumbnail_url,
            "items_count": len(t.items)
        } for t in templates
    ]), 200

@app.route("/api/community/import/<int:template_id>", methods=["POST"])
def import_community_checklist(template_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"message": "Missing user_id"}), 400

    template = db.session.get(CommunityChecklist, template_id)
    if not template:
        return jsonify({"message": "Template not found"}), 404

    new_game = Game(
        user_id=user_id,
        title=template.title,
        platform=template.platform,
        genre=template.genre,
        run_type=template.run_type,
        tags=template.tags,
        cover_url=template.thumbnail_url,
        thumbnail_url=template.thumbnail_url
    )
    db.session.add(new_game)
    db.session.flush()

    # copy items
    for itm in template.items:
        db.session.add(ChecklistItem(
            game_id=new_game.game_id,
            description=itm.description,
            completed=False,
            order=itm.order
        ))

    db.session.commit()
    return jsonify({
        "message": "Checklist imported",
        "new_game_id": new_game.game_id
    }), 201

@app.route("/api/community", methods=["POST"])
def create_community_checklist():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    created_by_user_id = data.get("created_by_user_id")
    if not title or not created_by_user_id:
        return jsonify({"message": "created_by_user_id and non-empty title are required"}), 400

    cc = CommunityChecklist(
        title=title,
        description=(data.get("description") or "").strip() or None,
        platform=(data.get("platform") or "").strip() or None,
        genre=(data.get("genre") or "").strip() or None,
        run_type=(data.get("run_type") or "").strip() or None,
        tags=(data.get("tags") or "").strip() or None,
        thumbnail_url=(data.get("thumbnail_url") or "").strip() or None,
        created_by_user_id=created_by_user_id,
    )
    db.session.add(cc)
    db.session.flush()  # get cc.community_checklist_id

    items = data.get("items") or []
    order_counter = 1
    for itm in items:
        if isinstance(itm, dict):
            desc = (itm.get("description") or "").strip()
            ordv = itm.get("order")
        else:
            desc = str(itm).strip()
            ordv = None
        if not desc:
            continue
        db.session.add(CommunityChecklistItem(
            community_checklist_id=cc.community_checklist_id,
            description=desc,
            order=ordv if isinstance(ordv, int) else order_counter
        ))
        order_counter += 1

    db.session.commit()
    return jsonify({
        "message": "Community checklist created",
        "community_checklist_id": cc.community_checklist_id
    }), 201

@app.route("/api/community/<int:template_id>", methods=["GET"])
def get_community_checklist(template_id):
    t = db.session.get(CommunityChecklist, template_id)
    if not t:
        return jsonify({"message": "Template not found"}), 404
    return jsonify(t.to_dict(include_items=True)), 200

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


@app.route("/admin/fix-timestamps", methods=["POST"])
def fix_timestamps():
    try:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()"))
            conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()"))
            conn.execute(text("UPDATE game SET created_at = NOW() WHERE created_at IS NULL"))
            conn.execute(text("UPDATE game SET updated_at = NOW() WHERE updated_at IS NULL"))
        return {"message": "created_at/updated_at ensured and backfilled"}, 200
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
