from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, db

def register_user():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'message': 'username, email, and password are required'}), 400

    # use db.select(...) instead of User.query for 3.x compatibility
    existing = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    if existing:
        return jsonify({'message': 'email already registered'}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    # returning user_id makes the frontend and Postman life easier
    return jsonify({'message': 'Registration successful', 'user_id': user.user_id}), 201


def login_user():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not password or not (email or username):
        return jsonify({'message': 'email or username and password required'}), 400

    q = db.select(User)
    q = q.filter_by(email=email) if email else q.filter_by(username=username)

    user = db.session.execute(q).scalar_one_or_none()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid email or password'}), 401

    return jsonify({'message': 'Logged in', 'user_id': user.user_id}), 200