# WPP Laptop Request System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based wizard form for WPP laptop requests that saves structured Markdown records to `/applications/`.

**Architecture:** Python Flask server serves a single-page vanilla HTML wizard form. The form collects laptop request data across 9 steps, POSTs JSON to `/api/save`, which validates and writes a Markdown file to the `applications/` directory with auto-incrementing sequence numbers.

**Tech Stack:** Python 3.10, Flask, vanilla HTML/CSS/JS

**Spec:** `docs/superpowers/specs/2026-03-19-laptop-request-system-design.md`

---

## File Structure

```
Application/
├── .gitignore             # Exclude venv, __pycache__, etc.
├── server.py              # Flask app: serves static files, POST /api/save, validation, MD generation
├── requirements.txt       # Flask pinned dependency
├── static/
│   └── index.html         # Single-file wizard: all HTML, CSS, JS embedded
├── applications/          # Output directory for generated MD files
│   └── .gitkeep
└── tests/
    ├── conftest.py        # Shared fixtures (client, tmp_path setup)
    └── test_server.py     # Server API tests: validation, file naming, MD generation
```

---

### Task 1: Project Setup — venv, Flask, requirements.txt

**Files:**
- Create: `requirements.txt`
- Create: `applications/.gitkeep`

- [ ] **Step 1: Create virtual environment**

Run:
```bash
cd /Users/chunyuanlu/WebApp/wpp-work/Application
python3 -m venv venv
```

- [ ] **Step 2: Create requirements.txt**

```
flask==3.1.0
pytest==8.3.4
```

- [ ] **Step 3: Install dependencies**

Run:
```bash
source venv/bin/activate
pip install -r requirements.txt
```
Expected: Successfully installed flask and pytest

- [ ] **Step 4: Create directories**

```bash
mkdir -p applications static tests
touch applications/.gitkeep
```

- [ ] **Step 5: Create .gitignore**

```
venv/
__pycache__/
*.pyc
.superpowers/
```

- [ ] **Step 6: Create tests/conftest.py**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
```

---

### Task 2: Flask Server — Skeleton with Health Check

**Files:**
- Create: `server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write the failing test for server health check**

Create `tests/test_server.py`:
```python
def test_health_check(client):
    rv = client.get('/api/health')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'ok'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py::test_health_check -v`
Expected: FAIL (cannot import server)

- [ ] **Step 3: Write minimal server.py**

Create `server.py`:
```python
import os
import json
import re
import glob
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS_DIR = os.path.join(BASE_DIR, 'applications')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR)

os.makedirs(APPLICATIONS_DIR, exist_ok=True)


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8900, debug=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py::test_health_check -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt server.py tests/test_server.py applications/.gitkeep static/
git commit -m "feat: scaffold Flask server with health check endpoint"
```

---

### Task 3: Server — File Naming and Sequence Logic

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing tests for filename generation**

Append to `tests/test_server.py`:
```python
from server import sanitize_company_name, generate_filename, APPLICATIONS_DIR
import tempfile
import shutil

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
        # Create existing files
        open(os.path.join(tmpdir, f"REQ-{today}-001-VML-Shanghai.md"), 'w').close()
        open(os.path.join(tmpdir, f"REQ-{today}-002-VML-Shanghai.md"), 'w').close()
        filename = generate_filename("VML Shanghai", tmpdir)
        assert filename == f"REQ-{today}-003-VML-Shanghai.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -k "sanitize or generate" -v`
Expected: FAIL (functions not defined)

- [ ] **Step 3: Implement sanitize_company_name and generate_filename**

Add to `server.py` (before the route definitions):
```python
def sanitize_company_name(name):
    sanitized = re.sub(r'[^a-zA-Z0-9]', '-', name)
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -k "sanitize or generate" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add filename generation with sequence auto-increment"
```

---

### Task 4: Server — Markdown Generation

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing test for MD generation**

Append to `tests/test_server.py`:
```python
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
    assert "## Replacement Details" not in md

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
    assert "Current Condition: Poor" in md
    assert "Diagnostics: Battery failing, keyboard issues" in md
    assert "[x] EUS team confirmed unfixable" in md
    assert "## New Hire Details" not in md
    assert "Urgent replacement needed" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -k "markdown" -v`
Expected: FAIL (generate_markdown not defined)

- [ ] **Step 3: Implement generate_markdown**

Add to `server.py`:
```python
def generate_markdown(data, request_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    req_type = "New Laptop" if data.get("requestType") == "new" else "Replacement Laptop"
    unit_cost = data.get("unitCost", 0)
    quantity = data.get("quantity", 1)
    total_cost = unit_cost * quantity
    currency = data.get("currency", "USD")

    def fmt_cost(val):
        return f"{val:,.0f}" if val == int(val) else f"{val:,.2f}"

    def checkbox(val):
        return "[x]" if val else "[ ]"

    lines = []
    lines.append(f"# Laptop Request — {request_id}")
    lines.append("")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Request ID:** {request_id}")
    lines.append("")

    # Request Type
    lines.append("## Request Type")
    lines.append(f"- Type: {req_type}")
    lines.append("")

    # Requestor Information
    lines.append("## Requestor Information")
    lines.append(f"- Name: {data.get('requestorName', '')}")
    lines.append(f"- Agency/Company: {data.get('agency', '')}")
    lines.append(f"- Market: {data.get('market', '')}")
    lines.append(f"- Email: {data.get('email', '')}")
    lines.append(f"- Staff Category: {data.get('staffCategory', 'Standard')}")
    lines.append("")

    # Stock Verification
    lines.append("## Stock Verification")
    lines.append(f"- {checkbox(data.get('stockNoBuffer'))} No buffer or almost-new laptops in existing stock")
    lines.append(f"- {checkbox(data.get('stockListingUpToDate'))} 2026 Stock listing file is up to date")
    lines.append("")

    # Laptop Specifications
    lines.append("## Laptop Specifications")
    lines.append(f"- EUC Persona: {data.get('eucPersona', '')}")
    lines.append(f"- EUC Standards Version: {data.get('eucStandardsVersion', '2025/Q4')}")
    lines.append(f"- Model: {data.get('laptopModel', '')}")
    lines.append(f"- OS: {data.get('os', '')}")
    mac_just = data.get('macOsJustification')
    lines.append(f"- macOS Justification: {mac_just if mac_just else 'N/A'}")
    lines.append(f"- Quantity: {quantity}")
    lines.append(f"- Specs: {data.get('specs', '')}")
    lines.append("")

    # Cost & Sourcing
    lines.append("## Cost & Sourcing")
    lines.append(f"- Unit Cost: {fmt_cost(unit_cost)} {currency}")
    lines.append(f"- Total Cost: {fmt_cost(total_cost)} {currency}")
    lines.append(f"- {checkbox(data.get('costFromDell'))} Cost from Dell Direct portal / approved partner")
    lines.append(f"- {checkbox(data.get('costExcludesTax'))} Cost excludes local taxes")
    lines.append("")

    # Conditional sections
    if data.get("requestType") == "new":
        lines.append("## New Hire Details")
        lines.append(f"- Number of New Hires: {data.get('newHireCount', '')}")
        lines.append(f"- Expected Join Date: {data.get('joinDate', '')}")
        persona = data.get('newHirePersona')
        lines.append(f"- EUC Persona Override: {persona if persona else 'N/A'}")
        lines.append(f"- Available Functional Laptops: {data.get('availableLaptops', '')}")
        lines.append("")
    elif data.get("requestType") == "replacement":
        lines.append("## Replacement Details")
        lines.append(f"- Current Condition: {data.get('currentCondition', '')}")
        lines.append(f"- Diagnostics: {data.get('diagnostics', '')}")
        lines.append(f"- {checkbox(data.get('eusConfirmed'))} EUS team confirmed unfixable")
        stock_just = data.get('stockNotUsedJustification')
        if stock_just:
            lines.append(f"- Why Existing Stock Not Used: {stock_just}")
        non_std = data.get('nonStandardJustification')
        if non_std:
            lines.append(f"- Non-Standard Config Justification: {non_std}")
        lines.append("")

    # Additional Comments
    lines.append("## Additional Comments")
    comments = data.get("comments", "").strip()
    lines.append(comments if comments else "(none)")
    lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -k "markdown" -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add Markdown generation for new and replacement requests"
```

---

### Task 5: Server — POST /api/save Endpoint with Validation

**Files:**
- Modify: `server.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Write failing tests for the save endpoint**

Append to `tests/test_server.py`:
```python
import tempfile
import shutil

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
    # Verify file was created
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

def test_save_macos_requires_justification(client, tmp_path, monkeypatch):
    monkeypatch.setattr('server.APPLICATIONS_DIR', str(tmp_path))
    bad_data = {**VALID_NEW_REQUEST, "os": "macOS", "macOsJustification": None}
    rv = client.post('/api/save', json=bad_data)
    assert rv.status_code == 400
    data = rv.get_json()
    assert 'macOsJustification' in str(data['details'])

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -k "save" -v`
Expected: FAIL (404 — route not defined)

- [ ] **Step 3: Implement /api/save with validation**

Add to `server.py`:
```python
def validate_request(data):
    errors = []
    # Required text fields
    for field in ['requestorName', 'agency', 'market', 'staffCategory']:
        if not data.get(field, '').strip():
            errors.append(f"{field} is required")

    # Email validation
    email = data.get('email', '')
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        errors.append("email format invalid")

    # Request type
    if data.get('requestType') not in ('new', 'replacement'):
        errors.append("requestType must be 'new' or 'replacement'")

    # Stock verification
    if not data.get('stockNoBuffer'):
        errors.append("stockNoBuffer confirmation is required")
    if not data.get('stockListingUpToDate'):
        errors.append("stockListingUpToDate confirmation is required")

    # Laptop specs
    if not data.get('eucPersona', '').strip():
        errors.append("eucPersona is required")
    if not data.get('laptopModel', '').strip():
        errors.append("laptopModel is required")
    if data.get('os') not in ('Windows', 'macOS'):
        errors.append("os must be 'Windows' or 'macOS'")
    if data.get('os') == 'macOS':
        if not data.get('macOsJustification') or not data.get('macOsJustification', '').strip():
            errors.append("macOsJustification is required when OS is macOS")

    # Non-standard config requires justification
    if data.get('eucPersona') == 'Other':
        if not data.get('nonStandardJustification') or not data.get('nonStandardJustification', '').strip():
            errors.append("nonStandardJustification is required when EUC Persona is Other")

    quantity = data.get('quantity')
    if not isinstance(quantity, (int, float)) or quantity < 1:
        errors.append("quantity must be a positive number")
    if not data.get('specs', '').strip():
        errors.append("specs is required")

    # Cost
    unit_cost = data.get('unitCost')
    if not isinstance(unit_cost, (int, float)) or unit_cost <= 0:
        errors.append("unitCost must be a positive number")
    if not data.get('currency', '').strip():
        errors.append("currency is required")
    if not data.get('costFromDell'):
        errors.append("costFromDell confirmation is required")
    if not data.get('costExcludesTax'):
        errors.append("costExcludesTax confirmation is required")

    # Conditional: New Laptop
    if data.get('requestType') == 'new':
        if not isinstance(data.get('newHireCount'), (int, float)) or data.get('newHireCount', 0) < 1:
            errors.append("newHireCount is required for new laptop requests")
        if not data.get('joinDate') or not str(data.get('joinDate', '')).strip():
            errors.append("joinDate is required for new laptop requests")
        if not data.get('availableLaptops') or not str(data.get('availableLaptops', '')).strip():
            errors.append("availableLaptops is required for new laptop requests")

    # Conditional: Replacement Laptop
    if data.get('requestType') == 'replacement':
        if not data.get('currentCondition') or not str(data.get('currentCondition', '')).strip():
            errors.append("currentCondition is required for replacement requests")
        if not data.get('diagnostics') or not str(data.get('diagnostics', '')).strip():
            errors.append("diagnostics is required for replacement requests")
        if not data.get('eusConfirmed'):
            errors.append("eusConfirmed is required for replacement requests")

    return errors


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

    return jsonify({
        'success': True,
        'filename': filename,
        'path': f'applications/{filename}'
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -k "save" -v`
Expected: All PASS

- [ ] **Step 5: Run all tests**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add server.py tests/test_server.py
git commit -m "feat: add POST /api/save with server-side validation"
```

---

### Task 6: Frontend — Wizard HTML with All 9 Steps

**Files:**
- Create: `static/index.html`

This is the largest task — the complete single-file wizard form with embedded CSS and JS.

- [ ] **Step 1: Create the complete index.html**

Create `static/index.html` with the following structure. This is a single file containing:
- CSS: WPP corporate style (navy blue `#0033A0`), progress bar, form styling, responsive layout
- HTML: 9 wizard steps, each in a `<div class="step">` with fields per spec
- JS: Step navigation, conditional step visibility (6 vs 7), validation per step, review summary generation, POST to `/api/save`, success/error display

The HTML should include:

**Header:** WPP logo area + "Laptop Request Form" title + progress bar (step indicators)

**Step 1 — Request Type:**
- Two styled radio cards: "New Laptop" and "Replacement Laptop"

**Step 2 — Requestor Info:**
- Text inputs: Name, Agency/Company, Market, Email
- Dropdown: Staff Category (Standard, WPP ET Staff, India HQ)

**Step 3 — Stock Verification:**
- Two checkboxes with descriptive labels
- Both required (validated before Next)

**Step 4 — Laptop Specs & Persona:**
- Dropdown: EUC Persona (Standard User, Power User, Developer, Senior Leader, Other)
- Read-only field: EUC Standards Version "2025/Q4"
- Text input: Laptop Model
- Dropdown: OS (Windows, macOS)
- Conditional textarea: macOS Justification (shown when macOS selected)
- Warning banner if staff category is WPP ET / India HQ
- Number input: Quantity
- Textarea: Specs Summary

**Step 5 — Cost & Sourcing:**
- Number input: Unit Cost
- Dropdown: Currency (USD, EUR, GBP, CNY, INR, SGD, AUD, BRL)
- Read-only: Total Cost (auto-calculated)
- Two confirmation checkboxes

**Step 6 — New Hire Details (shown only when requestType = "new"):**
- Number input: Number of new hires
- Date input: Expected join date
- Dropdown: EUC Persona Override (optional)
- Textarea: Available functional laptops

**Step 7 — Replacement Details (shown only when requestType = "replacement"):**
- Dropdown: Current laptop condition (Poor, Non-functional, Damaged, Outdated)
- Textarea: Diagnostics performed
- Checkbox: EUS team confirmed unfixable
- Textarea: Why existing stock can't be used (optional, note for Senior Leader)
- Textarea: Non-standard config justification (shown when persona = Other)

**Step 8 — Additional Comments:**
- Textarea: Comments (optional)

**Step 9 — Review & Submit:**
- Read-only summary of all fields grouped by section
- "Edit" buttons per section that jump back to that step
- "Submit Request" button
- Success message with filename after save
- "New Request" button to reset form

**JavaScript logic:**
- `currentStep` tracker, `nextStep()`, `prevStep()`, `goToStep(n)` functions
- `getVisibleSteps()` — returns array of step numbers based on request type (skips 6 or 7)
- `validateStep(n)` — validates current step fields, shows inline errors
- `updateProgressBar()` — updates step indicators
- `updateReviewSummary()` — builds Step 9 content from form data
- `submitRequest()` — collects all form data into JSON, POST to `/api/save`, handles response
- Event listeners: OS dropdown → show/hide macOS justification, Unit cost/quantity → update total, Request type → update visible steps

- [ ] **Step 2: Verify the form loads in the browser**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python server.py &`
Open: http://localhost:8900
Verify: Form loads with Step 1 visible, progress bar shows step 1 of 9, WPP navy blue styling

- [ ] **Step 3: Test wizard navigation**

Verify in browser:
- Select "New Laptop" → click Next → Step 2 loads
- Fill required fields → click Next through each step
- Step 6 appears (New Hire), Step 7 is skipped
- Go back to Step 1, select "Replacement" → Step 7 appears, Step 6 is skipped
- Step 9 shows review summary with all entered data
- "Edit" buttons jump back to correct steps

- [ ] **Step 4: Test form submission**

Verify in browser:
- Complete all steps with valid data
- Click "Submit Request" on Step 9
- Success message appears with filename
- Check `/applications/` directory — MD file exists with correct content

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat: add complete 9-step wizard form with WPP corporate styling"
```

---

### Task 7: Frontend Polish & Edge Cases

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Add inline validation error styling**

Verify each step shows red border + error message on invalid fields when Next is clicked without filling required fields.

- [ ] **Step 2: Test macOS justification conditional**

- Select macOS in Step 4 → justification textarea appears
- Set staff category to "WPP ET Staff" in Step 2 → warning banner shown in Step 4
- Switch back to Windows → justification hides
- Try to proceed with macOS selected but no justification → error shown

- [ ] **Step 3: Test cost auto-calculation**

- Enter unit cost 1200, quantity 3 → total shows 3,600
- Change quantity to 5 → total updates to 6,000
- Change unit cost to 0 → validation prevents proceeding

- [ ] **Step 4: Test review summary edit buttons**

- Complete form to Step 9
- Click "Edit" on Requestor Info → jumps to Step 2
- Change a field → navigate back to Step 9
- Verify summary reflects the change

- [ ] **Step 5: Test "New Request" reset**

- After successful submission, click "New Request"
- Form resets to Step 1 with all fields cleared

- [ ] **Step 6: Commit any fixes**

```bash
git add static/index.html
git commit -m "fix: polish form validation, edge cases, and reset behavior"
```

---

### Task 8: End-to-End Verification

**Files:** None (testing only)

- [ ] **Step 1: Run all server tests**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && venv/bin/pytest tests/test_server.py -v`
Expected: All PASS

- [ ] **Step 2: Full New Laptop flow**

Open http://localhost:8900 and complete a full New Laptop request:
1. Select "New Laptop"
2. Fill: Name "Test User", Agency "VML Shanghai", Market "China", Email "test@vml.com", Staff Category "Standard"
3. Check both stock verification boxes
4. Fill: Persona "Standard User", Model "Dell Latitude 5550", OS "Windows", Qty 2, Specs "16GB RAM"
5. Fill: Cost 1200, Currency USD, check both cost confirmations
6. Fill: 2 new hires, join date 2026-05-01, "No functional laptops available"
7. Add comments (optional)
8. Review and submit
9. Verify MD file in `/applications/`

- [ ] **Step 3: Full Replacement Laptop flow**

Repeat with Replacement Laptop path:
1. Select "Replacement Laptop"
2. Fill requestor info with Staff Category "WPP ET Staff"
3. Stock verification
4. Select macOS → fill justification (verify WPP ET warning appears)
5. Cost info
6. Fill: Condition "Poor", Diagnostics "Battery failing", check EUS confirmed
7. Comments
8. Review and submit
9. Verify MD file — should be sequence 002

- [ ] **Step 4: Verify sequence numbering**

Check `/applications/` — should have:
- `REQ-2026-03-19-001-VML-Shanghai.md`
- `REQ-2026-03-19-002-VML-Shanghai.md`

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: WPP Laptop Request System - complete implementation"
```
