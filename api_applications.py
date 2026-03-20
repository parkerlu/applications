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


@applications_bp.route('/api/applications/<app_id>/pdf', methods=['GET'])
@login_required
def get_application_pdf(app_id):
    """Generate and download a PDF for a single application."""
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

    app_data = _app_to_dict(app_doc)
    pdf_bytes = _generate_pdf(app_data)
    filename = f"{app_data['request_id']}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
    )


def _generate_pdf(app_data):
    from fpdf import FPDF

    d = app_data.get('data', {})
    req_id = app_data.get('request_id', '')
    status = app_data.get('status', '')
    created = (app_data.get('created_at') or '')[:10]
    type_label = 'New Laptop' if d.get('requestType') == 'new' else 'Replacement Laptop' if d.get('requestType') == 'replacement' else d.get('requestType', '')

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Header
    pdf.set_fill_color(15, 82, 186)
    pdf.rect(0, 0, 210, 28, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_xy(10, 6)
    pdf.cell(0, 8, f'WPP Laptop Request - {req_id}', ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_x(10)
    pdf.cell(0, 5, f'Generated {datetime.now().strftime("%Y-%m-%d")}')
    pdf.ln(14)

    def safe(val):
        if val is None:
            return ''
        return str(val)

    def section(title):
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(15, 82, 186)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_draw_color(200, 210, 230)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)

    def row(label, val):
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(60, 6, label)
        pdf.set_text_color(30, 30, 30)
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(0, 6, safe(val), ln=True)

    section('Request Info')
    row('Request ID', req_id)
    row('Status', status)
    row('Request Type', type_label)
    row('Submitted', created)
    pdf.ln(3)

    section('Requestor Information')
    row('Name', d.get('requestorName'))
    row('Email', d.get('email'))
    row('OpCo', d.get('agency'))
    row('Market', d.get('market'))
    row('EUS Lead Email', d.get('eusLeadEmail') or d.get('cityLeader'))
    row('BU Email', d.get('buEmail'))
    row('Date Required', d.get('dateRequired'))
    row('Staff Category', d.get('staffCategory'))
    pdf.ln(3)

    section('Device Specifications')
    row('EUC Persona', d.get('eucPersona'))
    row('Device Type', 'Desktop' if d.get('deviceType') == 'desktop' else 'Laptop')
    row('Device Model', d.get('laptopModel'))
    row('Make', d.get('selectedDeviceMake'))
    row('MPN', d.get('selectedDeviceMpn'))
    row('Operating System', d.get('os'))
    row('Quantity', d.get('quantity'))
    row('Specs', d.get('specs'))
    pdf.ln(3)

    section('Cost & Sourcing')
    unit = d.get('unitCost', '')
    qty = d.get('quantity', '')
    currency = d.get('currency', 'USD')
    row('Unit Cost', f'{unit} {currency}' if unit else '')
    try:
        total = float(unit) * int(qty)
        row('Total Cost', f'{total:.2f} {currency}')
    except (ValueError, TypeError):
        row('Total Cost', '')
    row('Local Currency', d.get('localCurrency'))
    row('Exchange Rate', d.get('exchangeRate'))
    row('Local Cost Per Device', d.get('localCostPerDevice'))
    pdf.ln(3)

    if d.get('requestType') == 'new':
        section('New Hire Details')
        row('Number of New Hires', d.get('newHireCount'))
        row('Expected Join Date', d.get('joinDate'))
        row('EUC Persona Override', d.get('newHirePersona'))
        row('Available Laptops', d.get('availableLaptops'))
        pdf.ln(3)

    if d.get('requestType') == 'replacement':
        section('Replacement Details')
        row('Current Device', f"{safe(d.get('currentDeviceMake'))} {safe(d.get('currentDeviceModel'))}")
        row('Serial Number', d.get('currentSerialNumber'))
        row('Device Age', f"{safe(d.get('currentDeviceAge'))} years" if d.get('currentDeviceAge') else '')
        row('Replacement Reason', d.get('currentCondition'))
        row('Diagnostics', d.get('diagnostics'))
        row('Current Workaround', d.get('currentWorkaround'))
        row('Workaround Details', d.get('workaroundDetails'))
        pdf.ln(3)

    section('Procurement Details')
    row('ET Legal Entity', d.get('etLegalEntity'))
    row('Lead Entity in Market', d.get('leadEntityInMarket'))
    row('BFC Code', d.get('bfcCode'))
    row('Stock or New Purchase', d.get('stockOrNewPurchase'))
    row('Transfer Entity', d.get('transferEntity'))
    row('Comments', d.get('comments'))

    return pdf.output()


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
