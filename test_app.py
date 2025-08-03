from app import app

def test_test_route():
    client = app.test_client()
    response = client.get('/api/test')
    assert response.status_code == 200
    assert response.get_json() == {'message': 'API is working'}

def test_register_user():
    client = app.test_client()
    payload = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "password123"
    }
    response = client.post('/api/register', json=payload)
    assert response.status_code == 201
    assert "Registration successful" in response.get_json()["message"]

def test_add_game():
    client = app.test_client()
    payload = {
        "user_id": 1,
        "title": "Test Game",
        "platform": "Test Platform",
        "genre": "Test Genre"
    }
    response = client.post('/api/games', json=payload)
    assert response.status_code == 201
    assert "game_id" in response.get_json()

def test_get_game():
    client = app.test_client()
    response = client.get('/api/games/1')  # Change to valid ID if needed
    assert response.status_code in [200, 404]  # Accept either based on if game exists
