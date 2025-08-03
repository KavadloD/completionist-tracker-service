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


def update_checklist_item(item_id):
    data = request.get_json()
    item = ChecklistItem.query.get(item_id)

    if not item:
        return jsonify({'message': 'Item not found'}), 404

    item.description = data.get('description', item.description)
    item.completed = data.get('completed', item.completed)
    item.order = data.get('order', item.order)

    db.session.commit()

    return jsonify({'message': 'Checklist item updated'}), 200

def delete_checklist_item(item_id):
    item = ChecklistItem.query.get(item_id)

    if not item:
        return jsonify({'message': 'Item not found'}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({'message': 'Checklist item deleted'}), 200
