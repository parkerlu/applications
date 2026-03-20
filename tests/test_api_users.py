import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId
import bcrypt


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_password_hash(password='password123'):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _make_user_doc(username='testuser', role='user', user_id=None):
    uid = user_id or ObjectId()
    from datetime import datetime, timezone
    return {
        '_id': uid,
        'username': username,
        'email': f'{username}@example.com',
        'name': username.title(),
        'opco': 'VML',
        'market': 'Shanghai',
        'role': role,
        'must_change_password': False,
        'password_hash': _make_password_hash(),
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        # Login as admin
        admin_doc = _make_user_doc('admin', 'admin')
        with patch('auth.get_db') as mock:
            mock_db = MagicMock()
            mock_db.users.find_one.return_value = admin_doc
            mock.return_value = mock_db
            with patch('auth.bcrypt.checkpw', return_value=True):
                client.post('/api/login', json={'username': 'admin', 'password': 'password123'})
        # Store admin_doc on client for reference
        client._admin_doc = admin_doc
        yield client


@pytest.fixture
def regular_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        # Login as regular user
        user_doc = _make_user_doc('regularuser', 'user')
        with patch('auth.get_db') as mock:
            mock_db = MagicMock()
            mock_db.users.find_one.return_value = user_doc
            mock.return_value = mock_db
            with patch('auth.bcrypt.checkpw', return_value=True):
                client.post('/api/login', json={'username': 'regularuser', 'password': 'password123'})
        client._user_doc = user_doc
        yield client


# ── tests ─────────────────────────────────────────────────────────────────────

def test_list_users_as_admin(admin_client):
    admin_doc = admin_client._admin_doc
    user1 = _make_user_doc('alice', 'user')
    user2 = _make_user_doc('bob', 'user')

    mock_db = MagicMock()
    mock_db.users.find_one.return_value = admin_doc
    mock_db.users.find.return_value = [admin_doc, user1, user2]

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = admin_client.get('/api/users')

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert len(data['users']) == 3
    usernames = [u['username'] for u in data['users']]
    assert 'admin' in usernames
    assert 'alice' in usernames
    assert 'bob' in usernames


def test_create_user_as_admin(admin_client):
    admin_doc = admin_client._admin_doc
    new_user_id = ObjectId()

    mock_db = MagicMock()
    mock_db.users.find_one.side_effect = [
        admin_doc,   # load_user call during request
        None,        # check for duplicate username
    ]
    mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)

    new_user_payload = {
        'username': 'newuser',
        'password': 'securepass',
        'email': 'newuser@example.com',
        'name': 'New User',
        'opco': 'VML',
        'market': 'Beijing',
        'role': 'user',
    }

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db), \
         patch('api_users.bcrypt.hashpw', return_value=b'$2b$12$fakehash'), \
         patch('api_users.bcrypt.gensalt', return_value=b'$2b$12$'):
        rv = admin_client.post('/api/users', json=new_user_payload)

    assert rv.status_code == 201
    data = rv.get_json()
    assert data['success'] is True
    assert data['user']['username'] == 'newuser'
    assert data['user']['email'] == 'newuser@example.com'
    assert data['user']['role'] == 'user'


def test_create_user_duplicate_username(admin_client):
    admin_doc = admin_client._admin_doc
    existing_user = _make_user_doc('existinguser', 'user')

    mock_db = MagicMock()
    mock_db.users.find_one.side_effect = [
        admin_doc,       # load_user call during request
        existing_user,   # duplicate username check returns a hit
    ]

    payload = {
        'username': 'existinguser',
        'password': 'somepassword',
        'email': 'dup@example.com',
        'name': 'Dup User',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': 'user',
    }

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = admin_client.post('/api/users', json=payload)

    assert rv.status_code == 409
    data = rv.get_json()
    assert data['success'] is False
    assert 'already exists' in data['error']


def test_non_admin_cannot_list_users(regular_client):
    user_doc = regular_client._user_doc

    mock_db = MagicMock()
    mock_db.users.find_one.return_value = user_doc

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = regular_client.get('/api/users')

    assert rv.status_code == 403
    data = rv.get_json()
    assert data['success'] is False
    assert 'Admin access required' in data['error']


def test_create_user_missing_fields(admin_client):
    admin_doc = admin_client._admin_doc
    mock_db = MagicMock()
    mock_db.users.find_one.return_value = admin_doc

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = admin_client.post('/api/users', json={'username': 'partial'})

    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False
    assert 'Missing required fields' in data['error']


def test_create_user_invalid_role(admin_client):
    admin_doc = admin_client._admin_doc
    mock_db = MagicMock()
    mock_db.users.find_one.side_effect = [admin_doc, None]

    payload = {
        'username': 'badroleuser',
        'password': 'pass123',
        'email': 'bad@example.com',
        'name': 'Bad Role',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': 'superadmin',
    }

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = admin_client.post('/api/users', json=payload)

    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False
    assert 'Role must be admin or user' in data['error']


def test_delete_user_not_found(admin_client):
    admin_doc = admin_client._admin_doc
    target_id = str(ObjectId())  # different from admin

    mock_db = MagicMock()
    mock_db.users.find_one.return_value = admin_doc
    mock_db.users.delete_one.return_value = MagicMock(deleted_count=0)

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = admin_client.delete(f'/api/users/{target_id}')

    assert rv.status_code == 404
    data = rv.get_json()
    assert data['success'] is False
    assert 'not found' in data['error']


def test_delete_self_forbidden(admin_client):
    admin_doc = admin_client._admin_doc
    admin_id = str(admin_doc['_id'])

    mock_db = MagicMock()
    mock_db.users.find_one.return_value = admin_doc

    with patch('auth.get_db', return_value=mock_db), \
         patch('api_users.get_db', return_value=mock_db):
        rv = admin_client.delete(f'/api/users/{admin_id}')

    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False
    assert 'Cannot delete yourself' in data['error']
