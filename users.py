from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db

def register_user():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Validate required fields FIRST
    if not all([username, email, password]):
        return jsonify({'message': 'username, email, and password are required'}), 400

    # Optional: deny duplicate emails (your column is unique, but this avoids a 500)
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'email already registered'}), 409

    hashed_pw = generate_password_hash(password)
    user = User(username=username, email=email, password_hash=hashed_pw)

    db.session.add(user)
    db.session.commit()

    return jsonify({'message': f'Registration successful for {username}'}), 201


def login_user():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({'message': 'email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid email or password'}), 401
