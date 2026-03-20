from datetime import datetime, timezone
from pymongo import MongoClient
import bcrypt

_client = None
_db = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient('localhost', 27017)
    return _client


def get_db():
    global _db
    if _db is None:
        _db = get_client().wpp_laptop
    return _db


def init_db():
    db = get_db()
    if db.users.count_documents({}) == 0:
        password_hash = bcrypt.hashpw(
            'admin123'.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')
        now = datetime.now(timezone.utc)
        db.users.insert_one({
            'username': 'admin',
            'password_hash': password_hash,
            'email': 'admin@wpp.com',
            'name': 'Administrator',
            'opco': 'WPP HQ',
            'market': 'Shanghai',
            'role': 'admin',
            'must_change_password': True,
            'created_at': now,
            'updated_at': now,
        })
        print('[INIT] Default admin created: admin / admin123')
