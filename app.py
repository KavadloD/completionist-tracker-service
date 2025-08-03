from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from models import db
from users import register_user, login_user
from models import Game
from flask import request, jsonify
from checklist import (
    add_checklist_item,
    get_checklist,
    update_checklist_item,
    delete_checklist_item
)


#password is postgres123
#port 5432

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres123@localhost/completionist_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)

@app.route('/api/test')
def test():
    return {'message': 'API is working'}

@app.route('/api/register', methods=['POST'])
def register():
    return register_user()

@app.route('/api/login', methods=['POST'])
def login():
    return login_user()

@app.route('/api/games/<int:game_id>/checklist', methods=['GET'])
def fetch_checklist(game_id):
    return get_checklist(game_id)

@app.route('/api/games/<int:game_id>/checklist', methods=['POST'])
def create_checklist_item(game_id):
    return add_checklist_item(game_id)

@app.route('/api/checklist/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    return update_checklist_item(item_id)

@app.route('/api/checklist/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    return delete_checklist_item(item_id)

@app.route('/api/games', methods=['POST'])
def add_game():
    data = request.get_json()
    game = Game(
        user_id=data.get('user_id'),
        title=data.get('title'),
        platform=data.get('platform'),
        genre=data.get('genre')
    )
    db.session.add(game)
    db.session.commit()
    return jsonify({'message': 'Game added', 'game_id': game.game_id}), 201

@app.route('/api/games/<int:game_id>', methods=['GET'])
def get_game(game_id):
    game = Game.query.get(game_id)
    if not game:
        return jsonify({'message': 'Game not found'}), 404

    return jsonify({
        'game_id': game.game_id,
        'user_id': game.user_id,
        'title': game.title,
        'platform': game.platform,
        'genre': game.genre
    })

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
def delete_game(game_id):
    game = Game.query.get(game_id)

    if not game:
        return jsonify({'message': 'Game not found'}), 404

    db.session.delete(game)
    db.session.commit()

    return jsonify({'message': 'Game deleted'}), 200


if __name__ == '__main__':
    app.run(debug=True)

