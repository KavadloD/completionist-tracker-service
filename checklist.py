from flask import request, jsonify
from models import db, ChecklistItem

def add_checklist_item(game_id):
    data = request.get_json()
    description = data.get('description')
    order = data.get('order', None)  # Optional

    item = ChecklistItem(
        game_id=game_id,
        description=description,
        order=order,
        completed=False
    )

    db.session.add(item)
    db.session.commit()

    return jsonify({'message': 'Checklist item added'}), 201

def get_checklist(game_id):
    items = ChecklistItem.query.filter_by(game_id=game_id).all()

    checklist = [{
        'id': item.checklist_item_id,
        'description': item.description,
        'completed': item.completed,
        'order': item.order
    } for item in items]

    return jsonify(checklist)
