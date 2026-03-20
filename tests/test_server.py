def test_health_check(client):
    rv = client.get('/api/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'ok'


from server import sanitize_company_name, generate_filename, APPLICATIONS_DIR
import tempfile
import os
from datetime import datetime

def test_sanitize_company_name_basic():
    assert sanitize_company_name("VML Shanghai") == "VML-Shanghai"

def test_sanitize_company_name_special_chars():
    assert sanitize_company_name("VML/Shanghai (China)") == "VML-Shanghai-China"

def test_sanitize_company_name_consecutive_hyphens():
    assert sanitize_company_name("VML -- Shanghai") == "VML-Shanghai"

def test_sanitize_company_name_trim_hyphens():
    assert sanitize_company_name("-VML Shanghai-") == "VML-Shanghai"

def test_generate_filename_first_of_day():
    with tempfile.TemporaryDirectory() as tmpdir:
        filename = generate_filename("VML Shanghai", tmpdir)
        today = datetime.now().strftime('%Y-%m-%d')
        assert filename == f"REQ-{today}-001-VML-Shanghai.md"

def test_generate_filename_increments_sequence():
    with tempfile.TemporaryDirectory() as tmpdir:
        today = datetime.now().strftime('%Y-%m-%d')
        open(os.path.join(tmpdir, f"REQ-{today}-001-VML-Shanghai.md"), 'w').close()
        open(os.path.join(tmpdir, f"REQ-{today}-002-VML-Shanghai.md"), 'w').close()
        filename = generate_filename("VML Shanghai", tmpdir)
        assert filename == f"REQ-{today}-003-VML-Shanghai.md"


from server import generate_markdown

def test_generate_markdown_new_laptop():
    data = {
        "requestType": "new",
        "requestorName": "John Doe",
        "agency": "VML Shanghai",
        "market": "China",
        "email": "john@vml.com",
        "staffCategory": "Standard",
        "stockNoBuffer": True,
        "stockListingUpToDate": True,
        "eucPersona": "Standard User",
        "eucStandardsVersion": "2025/Q4",
        "laptopModel": "Dell Latitude 5550",
        "os": "Windows",
        "macOsJustification": None,
        "quantity": 3,
        "specs": "16GB RAM, 512GB SSD",
        "unitCost": 1200,
        "currency": "USD",
        "costFromDell": True,
        "costExcludesTax": True,
        "newHireCount": 3,
        "joinDate": "2026-04-15",
        "newHirePersona": "Standard User",
        "availableLaptops": "No functional laptops available",
        "currentCondition": None,
        "diagnostics": None,
        "eusConfirmed": None,
        "stockNotUsedJustification": None,
        "nonStandardJustification": None,
        "comments": ""
    }
    request_id = "REQ-2026-03-19-001-VML-Shanghai"
    md = generate_markdown(data, request_id)
    assert f"# Laptop Request — {request_id}" in md
    assert "Type: New Laptop" in md
    assert "Name: John Doe" in md
    assert "Agency/Company: VML Shanghai" in md
    assert "EUC Persona: Standard User" in md
    assert "Unit Cost: 1,200 USD" in md
    assert "Total Cost: 3,600 USD" in md
    assert "Number of New Hires: 3" in md
    assert "## Replacement Reason" not in md

def test_generate_markdown_replacement_laptop():
    data = {
        "requestType": "replacement",
        "requestorName": "Jane Smith",
        "agency": "VML Shanghai",
        "market": "China",
        "email": "jane@vml.com",
        "staffCategory": "WPP ET Staff",
        "stockNoBuffer": True,
        "stockListingUpToDate": True,
        "eucPersona": "Power User",
        "eucStandardsVersion": "2025/Q4",
        "laptopModel": "Dell Latitude 7450",
        "os": "macOS",
        "macOsJustification": "Design work requires macOS-specific tools",
        "quantity": 1,
        "specs": "32GB RAM, 1TB SSD",
        "unitCost": 2500,
        "currency": "USD",
        "costFromDell": True,
        "costExcludesTax": True,
        "newHireCount": None,
        "joinDate": None,
        "newHirePersona": None,
        "availableLaptops": None,
        "currentCondition": "Poor",
        "diagnostics": "Battery failing, keyboard issues",
        "eusConfirmed": True,
        "stockNotUsedJustification": "No macOS devices in stock",
        "nonStandardJustification": None,
        "comments": "Urgent replacement needed"
    }
    request_id = "REQ-2026-03-19-002-VML-Shanghai"
    md = generate_markdown(data, request_id)
    assert "Type: Replacement Laptop" in md
    assert "macOS Justification: Design work requires macOS-specific tools" in md
    assert "Reason: Poor" in md
    assert "Issue Details: Battery failing, keyboard issues" in md
    assert "[x] EUS / IT Support confirmed unfixable" in md
    assert "## New Hire Details" not in md
    assert "Urgent replacement needed" in md


VALID_NEW_REQUEST = {
    "requestType": "new",
    "requestorName": "John Doe",
    "agency": "VML Shanghai",
    "market": "China",
    "email": "john@vml.com",
    "staffCategory": "Standard",
    "stockNoBuffer": True,
    "stockListingUpToDate": True,
    "eucPersona": "Standard User",
    "eucStandardsVersion": "2025/Q4",
    "laptopModel": "Dell Latitude 5550",
    "os": "Windows",
    "macOsJustification": None,
    "quantity": 3,
    "specs": "16GB RAM, 512GB SSD",
    "unitCost": 1200,
    "currency": "USD",
    "costFromDell": True,
    "costExcludesTax": True,
    "newHireCount": 3,
    "joinDate": "2026-04-15",
    "newHirePersona": None,
    "availableLaptops": "No functional laptops available",
    "currentCondition": None,
    "diagnostics": None,
    "eusConfirmed": None,
    "stockNotUsedJustification": None,
    "nonStandardJustification": None,
    "comments": ""
}

def test_save_valid_new_request(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    rv = client.post('/api/save', json=VALID_NEW_REQUEST)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert data['filename'].startswith('REQ-')
    assert data['filename'].endswith('.md')
    files = list(tmp_path.glob('REQ-*.md'))
    assert len(files) == 1

def test_save_missing_required_field(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "requestorName": ""}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False
    assert 'requestorName' in str(data['details'])

def test_save_invalid_email(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "email": "not-an-email"}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400
    data = rv.get_json()
    assert data['success'] is False

def test_save_macos_justification_is_optional(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    data_with_mac = {**VALID_NEW_REQUEST, "os": "macOS", "macOsJustification": None}
    rv = client.post('/api/save', json=data_with_mac)
    assert rv.status_code == 200

def test_save_stock_verification_required(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "stockNoBuffer": False}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_quantity_must_be_positive(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "quantity": 0}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_unit_cost_must_be_positive(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "unitCost": -100}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_cost_confirmations_required(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "costFromDell": False}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_new_hire_fields_required(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "joinDate": None}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

VALID_REPLACEMENT_REQUEST = {
    "requestType": "replacement",
    "requestorName": "Jane Smith",
    "agency": "VML Shanghai",
    "market": "China",
    "email": "jane@vml.com",
    "staffCategory": "WPP ET Staff",
    "stockNoBuffer": True,
    "stockListingUpToDate": True,
    "eucPersona": "Power User",
    "eucStandardsVersion": "2025/Q4",
    "laptopModel": "Dell Latitude 7450",
    "os": "macOS",
    "macOsJustification": "Design work requires macOS-specific tools",
    "quantity": 1,
    "specs": "32GB RAM, 1TB SSD",
    "unitCost": 2500,
    "currency": "USD",
    "costFromDell": True,
    "costExcludesTax": True,
    "newHireCount": None,
    "joinDate": None,
    "newHirePersona": None,
    "availableLaptops": None,
    "currentCondition": "Poor",
    "diagnostics": "Battery failing, keyboard issues",
    "eusConfirmed": True,
    "stockNotUsedJustification": "No macOS devices in stock",
    "nonStandardJustification": None,
    "comments": "Urgent"
}

def test_save_valid_replacement_request(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    rv = client.post('/api/save', json=VALID_REPLACEMENT_REQUEST)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True

def test_save_replacement_requires_condition(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_REPLACEMENT_REQUEST, "currentCondition": None}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_replacement_requires_diagnostics(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_REPLACEMENT_REQUEST, "diagnostics": None}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_replacement_requires_eus_confirmed(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_REPLACEMENT_REQUEST, "eusConfirmed": False}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400

def test_save_persona_other_requires_justification(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "eucPersona": "Other", "nonStandardJustification": None}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400
