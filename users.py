from flask import request, jsonify

def register_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # You’ll add real user creation later
    return jsonify({
        'message': f'Registration successful for {username}'
    }), 201

def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    #placeholder for rn
    return jsonify({
    'message': 'Login successful for ' + email
    }), 200
