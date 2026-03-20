from flask import Blueprint, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timezone
from bson import ObjectId
import bcrypt
from db import get_db

auth_bp = Blueprint('auth', __name__)
login_manager = LoginManager()


class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc['_id'])
        self.username = user_doc['username']
        self.email = user_doc['email']
        self.name = user_doc['name']
        self.opco = user_doc['opco']
        self.market = user_doc['market']
        self.role = user_doc['role']
        self.must_change_password = user_doc.get('must_change_password', False)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'opco': self.opco,
            'market': self.market,
            'role': self.role,
            'must_change_password': self.must_change_password,
        }


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_doc = db.users.find_one({'_id': ObjectId(user_id)})
    if user_doc:
        return User(user_doc)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'success': False, 'error': 'Authentication required'}), 401


def init_login(app):
    app.config.setdefault('SECRET_KEY', 'wpp-laptop-secret-key-change-me')
    login_manager.init_app(app)


@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    username = data.get('username', '').strip()
    password = data.get('password', '')
    db = get_db()
    user_doc = db.users.find_one({'username': username})
    if not user_doc:
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    if not bcrypt.checkpw(password.encode('utf-8'), user_doc['password_hash'].encode('utf-8')):
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    user = User(user_doc)
    login_user(user)
    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    logout_user()
    return jsonify({'success': True})


@auth_bp.route('/api/me')
@login_required
def me():
    return jsonify({'success': True, 'user': current_user.to_dict()})


@auth_bp.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    db = get_db()
    user_doc = db.users.find_one({'_id': ObjectId(current_user.id)})
    if not bcrypt.checkpw(old_password.encode('utf-8'), user_doc['password_hash'].encode('utf-8')):
        return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
    new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': {'password_hash': new_hash, 'must_change_password': False, 'updated_at': datetime.now(timezone.utc)}}
    )
    return jsonify({'success': True})


@auth_bp.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    update_fields = {'updated_at': datetime.now(timezone.utc)}
    new_email = data.get('email', '').strip()
    new_market = data.get('market', '').strip()
    if new_email:
        update_fields['email'] = new_email
    if new_market:
        update_fields['market'] = new_market

    db = get_db()

    # Only change password if provided
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if old_password and new_password:
        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        user_doc = db.users.find_one({'_id': ObjectId(current_user.id)})
        if not bcrypt.checkpw(old_password.encode('utf-8'), user_doc['password_hash'].encode('utf-8')):
            return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        update_fields['password_hash'] = new_hash
        update_fields['must_change_password'] = False

    db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {'$set': update_fields}
    )
    return jsonify({'success': True})
