from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone
from bson import ObjectId
import bcrypt
from db import get_db
from functools import wraps

users_bp = Blueprint('users', __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def _user_to_dict(user_doc):
    return {
        'id': str(user_doc['_id']),
        'username': user_doc['username'],
        'email': user_doc.get('email', ''),
        'name': user_doc.get('name', ''),
        'opco': user_doc.get('opco', ''),
        'market': user_doc.get('market', ''),
        'role': user_doc.get('role', 'user'),
        'created_at': user_doc['created_at'].isoformat() if user_doc.get('created_at') else None,
    }


@users_bp.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    db = get_db()
    users = list(db.users.find({}))
    return jsonify({'success': True, 'users': [_user_to_dict(u) for u in users]})


@users_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    required_fields = ['username', 'password', 'email', 'name', 'opco', 'market', 'role']
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'error': f'Missing required fields: {", ".join(missing)}'}), 400

    role = data['role']
    if role not in ('admin', 'user'):
        return jsonify({'success': False, 'error': 'Role must be admin or user'}), 400

    db = get_db()
    existing = db.users.find_one({'username': data['username']})
    if existing:
        return jsonify({'success': False, 'error': 'Username already exists'}), 409

    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    now = datetime.now(timezone.utc)
    new_user = {
        'username': data['username'],
        'password_hash': password_hash,
        'email': data['email'],
        'name': data['name'],
        'opco': data['opco'],
        'market': data['market'],
        'role': role,
        'must_change_password': True,
        'created_at': now,
        'updated_at': now,
    }
    result = db.users.insert_one(new_user)
    new_user['_id'] = result.inserted_id
    return jsonify({'success': True, 'user': _user_to_dict(new_user)}), 201


@users_bp.route('/api/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid user ID'}), 400

    db = get_db()
    user_doc = db.users.find_one({'_id': oid})
    if not user_doc:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    updates = {}
    for field in ('email', 'name', 'opco', 'market', 'role'):
        if field in data:
            if field == 'role' and data[field] not in ('admin', 'user'):
                return jsonify({'success': False, 'error': 'Role must be admin or user'}), 400
            updates[field] = data[field]

    if 'password' in data and data['password']:
        updates['password_hash'] = bcrypt.hashpw(
            data['password'].encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    if not updates:
        return jsonify({'success': False, 'error': 'No fields to update'}), 400

    updates['updated_at'] = datetime.now(timezone.utc)
    db.users.update_one({'_id': oid}, {'$set': updates})
    updated_doc = db.users.find_one({'_id': oid})
    return jsonify({'success': True, 'user': _user_to_dict(updated_doc)})


@users_bp.route('/api/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400

    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid user ID'}), 400

    db = get_db()
    result = db.users.delete_one({'_id': oid})
    if result.deleted_count == 0:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    return jsonify({'success': True})
