from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db  # Make sure to import your model and db

def register_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    hashed_pw = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=hashed_pw)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': f'Registration successful for {username}'
    }), 201

def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid email or password'}), 401
