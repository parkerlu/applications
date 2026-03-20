import os
import re
import glob
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory
from flask_login import login_required, current_user
from bson import ObjectId

from utils import sanitize_company_name, validate_request, generate_markdown, generate_excel_workbook
from auth import auth_bp, init_login
from api_users import users_bp
from api_applications import applications_bp, generate_request_id
from db import init_db, get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS_DIR = os.path.join(BASE_DIR, 'applications')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)
app.config['SECRET_KEY'] = 'wpp-laptop-secret-key-change-me'

os.makedirs(APPLICATIONS_DIR, exist_ok=True)

# Initialize auth and register blueprints
init_login(app)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(applications_bp)


def generate_filename(agency, applications_dir=None):
    if applications_dir is None:
        applications_dir = APPLICATIONS_DIR
    today = datetime.now().strftime('%Y-%m-%d')
    pattern = os.path.join(applications_dir, f"REQ-{today}-*.md")
    existing = glob.glob(pattern)
    max_seq = 0
    for f in existing:
        basename = os.path.basename(f)
        match = re.match(r'REQ-\d{4}-\d{2}-\d{2}-(\d{3})-', basename)
        if match:
            seq = int(match.group(1))
            if seq > max_seq:
                max_seq = seq
    next_seq = f"{max_seq + 1:03d}"
    company = sanitize_company_name(agency)
    return f"REQ-{today}-{next_seq}-{company}.md"


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/login')
def login_page():
    return send_from_directory(STATIC_DIR, 'login.html')


@app.route('/dashboard')
def dashboard():
    return send_from_directory(STATIC_DIR, 'dashboard.html')


@app.route('/api/save', methods=['POST'])
@login_required
def save_request():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided', 'details': []}), 400
    errors = validate_request(data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400
    request_id = generate_request_id(data.get('agency', 'Unknown'))
    now = datetime.now(timezone.utc)
    app_doc = {
        'request_id': request_id,
        'user_id': ObjectId(current_user.id),
        'status': 'submitted',
        'data': data,
        'created_at': now,
        'updated_at': now,
    }
    db = get_db()
    result = db.applications.insert_one(app_doc)
    return jsonify({'success': True, 'request_id': request_id, 'id': str(result.inserted_id)})


@app.route('/applications/<path:filename>')
def download_file(filename):
    return send_from_directory(APPLICATIONS_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8900, debug=True)
