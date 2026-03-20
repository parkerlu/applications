import io
import re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from bson import ObjectId
from db import get_db
from utils import validate_request, generate_excel_workbook, sanitize_company_name

applications_bp = Blueprint('applications', __name__)


def generate_request_id(opco):
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    sanitized = sanitize_company_name(opco)
    pattern = f'^REQ-{today}-'
    existing = db.applications.find({'request_id': {'$regex': pattern}})
    max_seq = 0
    for app in existing:
        match = re.match(r'REQ-\d{4}-\d{2}-\d{2}-(\d{3})-', app['request_id'])
        if match:
            seq = int(match.group(1))
            if seq > max_seq:
                max_seq = seq
    return f"REQ-{today}-{max_seq + 1:03d}-{sanitized}"


def _app_to_dict(app_doc):
    return {
        'id': str(app_doc['_id']),
        'request_id': app_doc['request_id'],
        'user_id': str(app_doc['user_id']),
        'status': app_doc.get('status', 'submitted'),
        'data': app_doc['data'],
        'created_at': app_doc['created_at'].isoformat() if app_doc.get('created_at') else None,
        'updated_at': app_doc['updated_at'].isoformat() if app_doc.get('updated_at') else None,
    }


# IMPORTANT: /export MUST be defined before /<app_id> to prevent Flask
# from matching "export" as an app_id value.

@applications_bp.route('/api/applications/export', methods=['GET'])
@login_required
def export_applications():
    """Batch export all visible applications as an Excel file."""
    db = get_db()
    if current_user.is_admin:
        apps = list(db.applications.find({}))
    else:
        apps = list(db.applications.find({'user_id': ObjectId(current_user.id)}))

    data_list = [a['data'] for a in apps]
    request_ids = [a['request_id'] for a in apps]

    wb = generate_excel_workbook(data_list, request_ids)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"applications-export-{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


@applications_bp.route('/api/applications', methods=['GET'])
@login_required
def list_applications():
    """List applications. Users see only their own; admins see all."""
    db = get_db()
    if current_user.is_admin:
        apps = list(db.applications.find({}))
    else:
        apps = list(db.applications.find({'user_id': ObjectId(current_user.id)}))

    return jsonify({'success': True, 'applications': [_app_to_dict(a) for a in apps]})


@applications_bp.route('/api/applications', methods=['POST'])
@login_required
def create_application():
    """Create a new application after validation."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided', 'details': []}), 400

    errors = validate_request(data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400

    opco = data.get('agency', 'Unknown')
    request_id = generate_request_id(opco)

    now = datetime.now(timezone.utc)
    doc = {
        'request_id': request_id,
        'user_id': ObjectId(current_user.id),
        'status': 'submitted',
        'data': data,
        'created_at': now,
        'updated_at': now,
    }

    db = get_db()
    result = db.applications.insert_one(doc)
    doc['_id'] = result.inserted_id

    return jsonify({'success': True, 'application': _app_to_dict(doc)}), 201


@applications_bp.route('/api/applications/<app_id>', methods=['GET'])
@login_required
def get_application(app_id):
    """Get a single application. Users can only access their own; admins can access all."""
    try:
        oid = ObjectId(app_id)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid application ID'}), 400

    db = get_db()
    app_doc = db.applications.find_one({'_id': oid})
    if not app_doc:
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    if not current_user.is_admin and str(app_doc['user_id']) != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    return jsonify({'success': True, 'application': _app_to_dict(app_doc)})


@applications_bp.route('/api/applications/<app_id>', methods=['PUT'])
@login_required
def update_application(app_id):
    """Update the data field of an application. Validates updated data."""
    try:
        oid = ObjectId(app_id)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid application ID'}), 400

    db = get_db()
    app_doc = db.applications.find_one({'_id': oid})
    if not app_doc:
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    if not current_user.is_admin and str(app_doc['user_id']) != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided', 'details': []}), 400

    errors = validate_request(data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400

    now = datetime.now(timezone.utc)
    db.applications.update_one(
        {'_id': oid},
        {'$set': {'data': data, 'updated_at': now}},
    )

    updated_doc = db.applications.find_one({'_id': oid})
    return jsonify({'success': True, 'application': _app_to_dict(updated_doc)})


@applications_bp.route('/api/applications/<app_id>', methods=['DELETE'])
@login_required
def delete_application(app_id):
    """Delete an application. Users can only delete their own; admins can delete all."""
    try:
        oid = ObjectId(app_id)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid application ID'}), 400

    db = get_db()
    app_doc = db.applications.find_one({'_id': oid})
    if not app_doc:
        return jsonify({'success': False, 'error': 'Application not found'}), 404

    if not current_user.is_admin and str(app_doc['user_id']) != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db.applications.delete_one({'_id': oid})
    return jsonify({'success': True, 'message': 'Application deleted'})
