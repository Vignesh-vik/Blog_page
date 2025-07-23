import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome' in response.data

def test_contact_form(client):
    response = client.post('/contact', data={
        'username': 'TestUser',
        'message': 'This is test feedback'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Feedback submitted successfully!' in response.data
