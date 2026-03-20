import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_user_doc(role='user', user_id=None):
    uid = user_id or ObjectId()
    return {
        '_id': uid,
        'username': 'testuser',
        'email': 'test@example.com',
        'name': 'Test User',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': role,
        'must_change_password': False,
        'password_hash': '$2b$12$validhashabcdefghijklmnopqrstuvwxyz012345',
    }


def _make_app_doc(user_id, app_id=None):
    oid = app_id or ObjectId()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return {
        '_id': oid,
        'request_id': f'REQ-2026-03-20-001-VML',
        'user_id': user_id,
        'status': 'submitted',
        'data': {'agency': 'VML', 'market': 'Shanghai'},
        'created_at': now,
        'updated_at': now,
    }


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user_client():
    from server import app
    from auth import auth_bp, init_login
    from api_applications import applications_bp
    if 'auth' not in app.blueprints:
        init_login(app)
        app.register_blueprint(auth_bp)
    if 'applications' not in app.blueprints:
        app.register_blueprint(applications_bp)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        user_doc = _make_user_doc('user')
        with patch('auth.get_db') as mock:
            mock_db = MagicMock()
            mock_db.users.find_one.return_value = user_doc
            mock.return_value = mock_db
            with patch('auth.bcrypt.checkpw', return_value=True):
                client.post('/api/login', json={'username': 'testuser', 'password': 'password123'})
        yield client, user_doc


@pytest.fixture
def admin_client():
    from server import app
    from auth import auth_bp, init_login
    from api_applications import applications_bp
    if 'auth' not in app.blueprints:
        init_login(app)
        app.register_blueprint(auth_bp)
    if 'applications' not in app.blueprints:
        app.register_blueprint(applications_bp)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        admin_doc = _make_user_doc('admin')
        with patch('auth.get_db') as mock:
            mock_db = MagicMock()
            mock_db.users.find_one.return_value = admin_doc
            mock.return_value = mock_db
            with patch('auth.bcrypt.checkpw', return_value=True):
                client.post('/api/login', json={'username': 'testuser', 'password': 'password123'})
        yield client, admin_doc


# ── tests ──────────────────────────────────────────────────────────────────────

def test_create_application(user_client):
    client, user_doc = user_client
    new_app_id = ObjectId()

    mock_db = MagicMock()
    mock_db.applications.find.return_value = []
    mock_db.applications.insert_one.return_value = MagicMock(inserted_id=new_app_id)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    inserted_doc = {
        '_id': new_app_id,
        'request_id': 'REQ-2026-03-20-001-VML',
        'user_id': user_doc['_id'],
        'status': 'submitted',
        'data': {'agency': 'VML'},
        'created_at': now,
        'updated_at': now,
    }
    mock_db.applications.find_one.return_value = inserted_doc

    with patch('api_applications.validate_request', return_value=[]), \
         patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.post('/api/applications', json={'agency': 'VML', 'market': 'Shanghai'})

    assert rv.status_code == 201
    data = rv.get_json()
    assert data['success'] is True
    assert 'application' in data


def test_list_own_applications(user_client):
    client, user_doc = user_client
    app_doc = _make_app_doc(user_doc['_id'])

    mock_db = MagicMock()
    mock_db.applications.find.return_value = [app_doc]

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.get('/api/applications')

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert len(data['applications']) == 1
    assert data['applications'][0]['request_id'] == app_doc['request_id']


def test_delete_own_application(user_client):
    client, user_doc = user_client
    app_id = ObjectId()
    app_doc = _make_app_doc(user_doc['_id'], app_id=app_id)

    mock_db = MagicMock()
    mock_db.applications.find_one.return_value = app_doc
    mock_db.applications.delete_one.return_value = MagicMock(deleted_count=1)

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.delete(f'/api/applications/{app_id}')

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    mock_db.applications.delete_one.assert_called_once()


def test_cannot_delete_others_application(user_client):
    client, user_doc = user_client
    other_user_id = ObjectId()  # different user
    app_id = ObjectId()
    app_doc = _make_app_doc(other_user_id, app_id=app_id)

    mock_db = MagicMock()
    mock_db.applications.find_one.return_value = app_doc

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.delete(f'/api/applications/{app_id}')

    assert rv.status_code == 403
    data = rv.get_json()
    assert data['success'] is False
    assert 'Access denied' in data['error']


def test_get_own_application(user_client):
    client, user_doc = user_client
    app_id = ObjectId()
    app_doc = _make_app_doc(user_doc['_id'], app_id=app_id)

    mock_db = MagicMock()
    mock_db.applications.find_one.return_value = app_doc

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.get(f'/api/applications/{app_id}')

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert data['application']['id'] == str(app_id)


def test_cannot_get_others_application(user_client):
    client, user_doc = user_client
    other_user_id = ObjectId()
    app_id = ObjectId()
    app_doc = _make_app_doc(other_user_id, app_id=app_id)

    mock_db = MagicMock()
    mock_db.applications.find_one.return_value = app_doc

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.get(f'/api/applications/{app_id}')

    assert rv.status_code == 403
    data = rv.get_json()
    assert data['success'] is False


def test_get_application_not_found(user_client):
    client, user_doc = user_client

    mock_db = MagicMock()
    mock_db.applications.find_one.return_value = None

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = user_doc
        auth_mock.return_value = auth_db

        rv = client.get(f'/api/applications/{ObjectId()}')

    assert rv.status_code == 404


def test_admin_can_list_all_applications(admin_client):
    client, admin_doc = admin_client
    app_doc_1 = _make_app_doc(ObjectId())
    app_doc_2 = _make_app_doc(ObjectId())

    mock_db = MagicMock()
    mock_db.applications.find.return_value = [app_doc_1, app_doc_2]

    with patch('api_applications.get_db', return_value=mock_db), \
         patch('auth.get_db') as auth_mock:
        auth_db = MagicMock()
        auth_db.users.find_one.return_value = admin_doc
        auth_mock.return_value = auth_db

        rv = client.get('/api/applications')

    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert len(data['applications']) == 2


def test_unauthenticated_cannot_access():
    """Verify unauthenticated access returns 401."""
    from server import app
    from auth import auth_bp, init_login
    from api_applications import applications_bp
    if 'auth' not in app.blueprints:
        init_login(app)
        app.register_blueprint(auth_bp)
    if 'applications' not in app.blueprints:
        app.register_blueprint(applications_bp)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    # Fresh client with no login session
    with app.test_client() as fresh_client:
        rv = fresh_client.get('/api/applications')
    assert rv.status_code == 401
