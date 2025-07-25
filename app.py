from flask import Flask
from users import register_user, login_user

app = Flask(__name__)

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
