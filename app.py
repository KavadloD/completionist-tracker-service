from flask import Flask
from users import register_user, login_user
from flask_sqlalchemy import SQLAlchemy
from models import db

#password is postgres123
#port 5432

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:postgres123@localhost/databasename'
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


if __name__ == '__main__':
    app.run(debug=True)

