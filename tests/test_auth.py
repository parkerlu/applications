import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId


# ── helpers ──────────────────────────────────────────────────────────────────

def make_user_doc(user_id=None, password_hash=None):
    """Return a minimal user document suitable for mocking find_one."""
    uid = user_id or ObjectId()
    return {
        '_id': uid,
        'username': 'testuser',
        'email': 'test@example.com',
        'name': 'Test User',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': 'user',
        'must_change_password': False,
        'password_hash': password_hash or '$2b$12$validhashabcdefghijklmnopqrstuvwxyz012345',
    }


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


# ── tests ─────────────────────────────────────────────────────────────────────

def test_login_success(auth_client):
    user_doc = make_user_doc()
    mock_db = MagicMock()
    mock_db.users.find_one.return_value = user_doc

    with patch('auth.get_db', return_value=mock_db), \
         patch('auth.bcrypt.checkpw', return_value=True):
        rv = auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'correctpassword',
        })

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert data['user']['username'] == 'testuser'


def test_login_wrong_password(auth_client):
    user_doc = make_user_doc()
    mock_db = MagicMock()
    mock_db.users.find_one.return_value = user_doc

    with patch('auth.get_db', return_value=mock_db), \
         patch('auth.bcrypt.checkpw', return_value=False):
        rv = auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'wrongpassword',
        })

    assert rv.status_code == 401
    data = rv.get_json()
    assert data['success'] is False
    assert 'Invalid credentials' in data['error']


def test_login_user_not_found(auth_client):
    mock_db = MagicMock()
    mock_db.users.find_one.return_value = None

    with patch('auth.get_db', return_value=mock_db):
        rv = auth_client.post('/api/login', json={
            'username': 'nobody',
            'password': 'whatever',
        })

    assert rv.status_code == 401
    data = rv.get_json()
    assert data['success'] is False
    assert 'Invalid credentials' in data['error']


def test_me_unauthenticated(auth_client):
    rv = auth_client.get('/api/me')
    assert rv.status_code == 401
    data = rv.get_json()
    assert data['success'] is False
    assert 'Authentication required' in data['error']


def test_logout(auth_client):
    rv = auth_client.post('/api/logout')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True


def test_change_password(auth_client):
    user_id = ObjectId()
    user_doc = make_user_doc(user_id=user_id)
    mock_db = MagicMock()
    mock_db.users.find_one.return_value = user_doc

    new_hash = b'$2b$12$newhash'

    with patch('auth.get_db', return_value=mock_db), \
         patch('auth.bcrypt.checkpw', return_value=True), \
         patch('auth.bcrypt.hashpw', return_value=new_hash), \
         patch('auth.bcrypt.gensalt', return_value=b'$2b$12$'):
        # Log in first
        rv = auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'oldpassword',
        })
        assert rv.status_code == 200

        # Now change password
        rv = auth_client.post('/api/change-password', json={
            'old_password': 'oldpassword',
            'new_password': 'newpassword123',
        })

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True


def test_change_password_too_short(auth_client):
    user_id = ObjectId()
    user_doc = make_user_doc(user_id=user_id)
    mock_db = MagicMock()
    mock_db.users.find_one.return_value = user_doc

    with patch('auth.get_db', return_value=mock_db), \
         patch('auth.bcrypt.checkpw', return_value=True):
        # Log in first
        rv = auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'oldpassword',
        })
        assert rv.status_code == 200

        # Attempt to change to a too-short password
        rv = auth_client.post('/api/change-password', json={
            'old_password': 'oldpassword',
            'new_password': 'abc',
        })

    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False
    assert 'at least 6 characters' in data['error']
