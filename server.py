import os
import re
import glob
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from utils import sanitize_company_name, validate_request, generate_markdown, generate_excel_workbook

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS_DIR = os.path.join(BASE_DIR, 'applications')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

os.makedirs(APPLICATIONS_DIR, exist_ok=True)


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


@app.route('/api/save', methods=['POST'])
def save_request():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided', 'details': []}), 400

    errors = validate_request(data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400

    filename = generate_filename(data.get('agency', 'Unknown'))
    request_id = filename.replace('.md', '')
    md_content = generate_markdown(data, request_id)

    filepath = os.path.join(APPLICATIONS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # Generate Excel file
    wb = generate_excel_workbook([data], [request_id])
    excel_path = os.path.join(APPLICATIONS_DIR, request_id + '.xlsx')
    wb.save(excel_path)
    excel_filename = request_id + '.xlsx'

    return jsonify({
        'success': True,
        'filename': filename,
        'excelFilename': excel_filename,
        'path': f'applications/{filename}'
    })


@app.route('/applications/<path:filename>')
def download_file(filename):
    return send_from_directory(APPLICATIONS_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8900, debug=True)
