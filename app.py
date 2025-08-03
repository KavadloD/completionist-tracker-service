from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db
from users import register_user, login_user
from checklist import add_checklist_item, get_checklist

#password is postgres123
#port 5432

app = Flask(__name__)
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


if __name__ == '__main__':
    app.run(debug=True)

