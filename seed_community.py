from app import app
from models import db, CommunityChecklist

sample_data = [
    CommunityChecklist(
        title="Hollow Knight – 100% Completion",
        description="All charms, grubs, bosses, and true ending.",
        platform="PC",
        genre="Metroidvania",
        created_by_user_id=1  # or use a real user_id if you have one
    ),
    CommunityChecklist(
        title="Final Fantasy X – Aeons and Side Quests",
        description="Capture monsters, get all celestial weapons, finish all side quests.",
        platform="PlayStation",
        genre="RPG",
        created_by_user_id=1
    ),
    CommunityChecklist(
        title="Metroid Prime – Minimal Item Run",
        description="No energy tanks, no missiles, hard mode speedrun.",
        platform="GameCube",
        genre="Action-Adventure",
        created_by_user_id=1
    ),
]

with app.app_context():
    db.session.bulk_save_objects(sample_data)
    db.session.commit()
    print("Sample community checklists added!")
