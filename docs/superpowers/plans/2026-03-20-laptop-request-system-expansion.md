# WPP Laptop Request System Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the existing Flask wizard into a full application with MongoDB storage, user authentication (admin/user roles), and CRUD management dashboard.

**Architecture:** Flask backend with Flask-Login for sessions, PyMongo for MongoDB. Three HTML pages: login, dashboard, wizard (existing index.html modified). MongoDB runs in Docker with volume persistence. Shared utilities (validation, Excel generation) extracted to `utils.py` to avoid circular imports between server.py and blueprint modules.

**Tech Stack:** Flask, Flask-Login, PyMongo (includes bson), bcrypt, openpyxl (existing), MongoDB 7 (Docker), vanilla JavaScript

**Spec:** `docs/superpowers/specs/2026-03-20-laptop-request-system-expansion-design.md`

---

## File Structure

### New Files
- `docker-compose.yml` — MongoDB container definition
- `db.py` — MongoDB connection and initialization (default admin user)
- `utils.py` — Shared utilities: validate_request(), generate_excel_workbook(), sanitize_company_name()
- `auth.py` — Authentication routes and Flask-Login setup
- `api_users.py` — User management API (admin-only CRUD)
- `api_applications.py` — Application CRUD API + batch export
- `static/login.html` — Login page
- `static/dashboard.html` — Dashboard with sidebar navigation

### Modified Files
- `server.py` — Register blueprints, import from utils.py, add Flask-Login init
- `static/index.html` — Add login guard, auto-fill from user profile, edit mode support
- `requirements.txt` — Add flask-login, pymongo, bcrypt
- `start.sh` — Add docker compose up before Flask start
- `tests/conftest.py` — Add MongoDB test fixtures
- `tests/test_server.py` — Update tests for new architecture (auth-aware)

---

### Task 1: Docker + MongoDB Setup

**Files:**
- Create: `docker-compose.yml`
- Modify: `start.sh`
- Modify: `requirements.txt`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
services:
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    environment:
      MONGO_INITDB_DATABASE: wpp_laptop

volumes:
  mongo_data:
```

- [ ] **Step 2: Update requirements.txt**

Add to existing file (keep existing flask, pytest, openpyxl):
```
flask-login==0.6.3
pymongo==4.12.1
bcrypt==4.3.0
```

- [ ] **Step 3: Update start.sh to start MongoDB first**

Add after `cd "$(dirname "$0")"` and before the venv block:
```bash
# Start MongoDB if not running
if ! docker compose ps --status running 2>/dev/null | grep -q mongodb; then
    echo "Starting MongoDB..."
    docker compose up -d
    sleep 2
fi
```

- [ ] **Step 4: Install new dependencies**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && pip install flask-login==0.6.3 pymongo==4.12.1 bcrypt==4.3.0`

- [ ] **Step 5: Start MongoDB and verify connection**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && docker compose up -d && python -c "from pymongo import MongoClient; c = MongoClient('localhost', 27017); print(c.server_info()['version'])"`
Expected: MongoDB version number printed

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml requirements.txt start.sh
git commit -m "feat: add Docker MongoDB and new dependencies"
```

---

### Task 2: Database Connection and Initialization

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing test for db initialization**

Create `tests/test_db.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from db import get_db, init_db


def test_init_db_creates_admin_when_users_empty():
    mock_db = MagicMock()
    mock_db.users.count_documents.return_value = 0
    mock_db.users.insert_one = MagicMock()

    with patch('db.get_db', return_value=mock_db):
        init_db()

    mock_db.users.insert_one.assert_called_once()
    call_args = mock_db.users.insert_one.call_args[0][0]
    assert call_args['username'] == 'admin'
    assert call_args['role'] == 'admin'
    assert call_args['must_change_password'] is True


def test_init_db_skips_when_users_exist():
    mock_db = MagicMock()
    mock_db.users.count_documents.return_value = 1

    with patch('db.get_db', return_value=mock_db):
        init_db()

    mock_db.users.insert_one.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Implement db.py**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add MongoDB connection and admin initialization"
```

---

### Task 3: Extract Shared Utilities to utils.py

**Files:**
- Create: `utils.py`
- Modify: `server.py`
- Modify: `tests/test_server.py`

This task extracts `validate_request()`, `generate_markdown()`, `generate_excel()`, and `sanitize_company_name()` out of `server.py` into `utils.py` to avoid circular imports when blueprints need these functions. Also refactors `generate_excel()` into `generate_excel_workbook()` that returns a Workbook (supporting multiple rows for batch export).

- [ ] **Step 1: Create utils.py**

Move `validate_request`, `generate_markdown`, `sanitize_company_name` from `server.py` into `utils.py` as-is. Refactor `generate_excel` into `generate_excel_workbook(data_list, request_ids)`:

```python
import re
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


def sanitize_company_name(name):
    sanitized = re.sub(r'[^a-zA-Z0-9]', '-', name)
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')
    return sanitized


def validate_request(data):
    """Validate a laptop request. Returns list of error strings (empty = valid)."""
    errors = []
    for field in ['requestorName', 'agency', 'market', 'staffCategory']:
        if not data.get(field, '').strip():
            errors.append(f"{field} is required")

    email = data.get('email', '')
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        errors.append("email format invalid")

    if data.get('requestType') not in ('new', 'replacement'):
        errors.append("requestType must be 'new' or 'replacement'")

    if not data.get('stockNoBuffer'):
        errors.append("stockNoBuffer confirmation is required")
    if not data.get('stockListingUpToDate'):
        errors.append("stockListingUpToDate confirmation is required")

    if not data.get('eucPersona', '').strip():
        errors.append("eucPersona is required")
    if not data.get('laptopModel', '').strip():
        errors.append("laptopModel is required")
    if data.get('os') not in ('Windows', 'macOS'):
        errors.append("os must be 'Windows' or 'macOS'")

    if data.get('deviceType') and data.get('deviceType') not in ('laptop', 'desktop'):
        errors.append("deviceType must be 'laptop' or 'desktop'")

    if data.get('eucPersona') == 'Other':
        if not data.get('nonStandardJustification') or not data.get('nonStandardJustification', '').strip():
            errors.append("nonStandardJustification is required when EUC Persona is Other")

    quantity = data.get('quantity')
    if not isinstance(quantity, (int, float)) or quantity < 1:
        errors.append("quantity must be a positive number")
    if not data.get('specs', '').strip():
        errors.append("specs is required")

    unit_cost = data.get('unitCost')
    if not isinstance(unit_cost, (int, float)) or unit_cost <= 0:
        errors.append("unitCost must be a positive number")
    if not data.get('currency', '').strip():
        errors.append("currency is required")
    if not data.get('costFromDell'):
        errors.append("costFromDell confirmation is required")
    if not data.get('costExcludesTax'):
        errors.append("costExcludesTax confirmation is required")

    if data.get('requestType') == 'new':
        if not isinstance(data.get('newHireCount'), (int, float)) or data.get('newHireCount', 0) < 1:
            errors.append("newHireCount is required for new laptop requests")
        if not data.get('joinDate') or not str(data.get('joinDate', '')).strip():
            errors.append("joinDate is required for new laptop requests")
        if not data.get('availableLaptops') or not str(data.get('availableLaptops', '')).strip():
            errors.append("availableLaptops is required for new laptop requests")

    if data.get('requestType') == 'replacement':
        if not data.get('currentCondition') or not str(data.get('currentCondition', '')).strip():
            errors.append("currentCondition is required for replacement requests")
        if not data.get('diagnostics') or not str(data.get('diagnostics', '')).strip():
            errors.append("diagnostics is required for replacement requests")
        if not data.get('eusConfirmed'):
            errors.append("eusConfirmed is required for replacement requests")

    if 'eusLeadEmail' in data:
        eus_email = data.get('eusLeadEmail', '')
        if not eus_email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', eus_email):
            errors.append("eusLeadEmail format invalid")
    if 'dateRequired' in data:
        if not data.get('dateRequired', '').strip():
            errors.append("dateRequired is required")
    if 'bfcCode' in data:
        if not data.get('bfcCode', '').strip():
            errors.append("bfcCode is required")
    if 'stockOrNewPurchase' in data:
        if not data.get('stockOrNewPurchase', '').strip():
            errors.append("stockOrNewPurchase is required")
    if 'etLegalEntity' in data:
        if not data.get('etLegalEntity', '').strip():
            errors.append("etLegalEntity is required")

    return errors


def generate_markdown(data, request_id):
    """Generate markdown content for a laptop request. Returns string."""
    # (Copy existing generate_markdown from server.py verbatim)
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
    lines.append("## Request Type")
    lines.append(f"- Type: {req_type}")
    lines.append("")
    lines.append("## Requestor Information")
    lines.append(f"- Name: {data.get('requestorName', '')}")
    lines.append(f"- Agency/Company: {data.get('agency', '')}")
    lines.append(f"- Market: {data.get('market', '')}")
    lines.append(f"- Email: {data.get('email', '')}")
    lines.append(f"- Staff Category: {data.get('staffCategory', 'Standard')}")
    lines.append("")
    lines.append("## Stock Verification")
    lines.append(f"- {checkbox(data.get('stockNoBuffer'))} No buffer or almost-new laptops in existing stock")
    lines.append(f"- {checkbox(data.get('stockListingUpToDate'))} 2026 Stock listing file is up to date")
    lines.append("")
    lines.append("## Laptop Specifications")
    lines.append(f"- EUC Persona: {data.get('eucPersona', '')}")
    lines.append(f"- EUC Standards Version: {data.get('eucStandardsVersion', '2025/Q4')}")
    device_type = data.get('deviceType', '')
    if device_type:
        lines.append(f"- Device Type: {device_type.capitalize()}")
    lines.append(f"- Model: {data.get('laptopModel', '')}")
    make = data.get('make', '')
    if make:
        lines.append(f"- Make: {make}")
    mpn = data.get('mpn', '')
    if mpn:
        lines.append(f"- MPN: {mpn}")
    lines.append(f"- OS: {data.get('os', '')}")
    mac_just = data.get('macOsJustification')
    lines.append(f"- macOS Justification: {mac_just if mac_just else 'N/A'}")
    lines.append(f"- Quantity: {quantity}")
    lines.append(f"- Specs: {data.get('specs', '')}")
    lines.append("")
    lines.append("## Cost & Sourcing")
    lines.append(f"- Unit Cost: {fmt_cost(unit_cost)} {currency}")
    lines.append(f"- Total Cost: {fmt_cost(total_cost)} {currency}")
    is_apple = data.get('os') == 'macOS' or (data.get('make', '') or '').lower() == 'apple'
    cost_source = "Cost from WPP designated supplier (Computacenter / Apple Direct)" if is_apple else "Cost from Dell Direct portal / approved partner"
    lines.append(f"- {checkbox(data.get('costFromDell'))} {cost_source}")
    lines.append(f"- {checkbox(data.get('costExcludesTax'))} Cost excludes local taxes")
    lines.append("")

    if data.get("requestType") == "new":
        lines.append("## New Hire Details")
        lines.append(f"- Number of New Hires: {data.get('newHireCount', '')}")
        lines.append(f"- Expected Join Date: {data.get('joinDate', '')}")
        persona = data.get('newHirePersona')
        lines.append(f"- EUC Persona Override: {persona if persona else 'N/A'}")
        lines.append(f"- Available Functional Laptops: {data.get('availableLaptops', '')}")
        lines.append("")
    elif data.get("requestType") == "replacement":
        lines.append("## Current Device Information")
        dev_make = data.get('currentDeviceMake', '')
        dev_model = data.get('currentDeviceModel', '')
        lines.append(f"- Current Device: {dev_make} {dev_model}")
        serial = data.get('currentSerialNumber')
        if serial:
            lines.append(f"- Serial Number: {serial}")
        dev_age = data.get('currentDeviceAge')
        if dev_age is not None:
            lines.append(f"- Device Age: {dev_age} years")
        dev_specs = data.get('currentDeviceSpecs')
        if dev_specs:
            lines.append(f"- Current Device Specs: {dev_specs}")
        lines.append("")
        lines.append("## Replacement Reason")
        lines.append(f"- Reason: {data.get('currentCondition', '')}")
        lines.append(f"- Issue Details: {data.get('diagnostics', '')}")
        lines.append(f"- {checkbox(data.get('eusConfirmed'))} EUS / IT Support confirmed unfixable")
        lines.append("")
        lines.append("## Current Workaround")
        workaround = data.get('currentWorkaround', '')
        lines.append(f"- Workaround: {workaround}")
        wa_details = data.get('workaroundDetails')
        if wa_details:
            lines.append(f"- Details: {wa_details}")
        lines.append("")
        lines.append("## Additional Justification")
        stock_just = data.get('stockNotUsedJustification')
        if stock_just:
            lines.append(f"- Why Existing Stock Not Used: {stock_just}")
        non_std = data.get('nonStandardJustification')
        if non_std:
            lines.append(f"- Non-Standard Config Justification: {non_std}")
        if not stock_just and not non_std:
            lines.append("(none)")
        lines.append("")

    lines.append("## Additional Comments")
    comments = data.get("comments", "").strip()
    lines.append(comments if comments else "(none)")
    lines.append("")

    return "\n".join(lines)


def _build_excel_row(data):
    """Build a single Excel data row from request data. Returns list of cell values."""
    os_val = data.get('os', '')
    device_type_str = "Mac" if os_val == "macOS" else "Windows"
    quantity = data.get('quantity', 1)
    unit_cost = data.get('unitCost', 0)

    if data.get('requestType') == 'new':
        rationale = "New Joiner - {} new hires joining {}. {}".format(
            data.get('newHireCount', ''),
            data.get('joinDate', ''),
            data.get('availableLaptops', '')
        )
    else:
        rationale = "{} - {} {} ({}yr). Workaround: {}".format(
            data.get('currentCondition', ''),
            data.get('currentDeviceMake', ''),
            data.get('currentDeviceModel', ''),
            data.get('currentDeviceAge', ''),
            data.get('currentWorkaround', '')
        )

    comments = data.get('comments', '') or ''
    comment_lines = []
    if data.get('requestType') == 'new':
        comment_lines.append(f"- Request Type: New Laptop")
        comment_lines.append(f"- Persona: {data.get('eucPersona', '')}")
        comment_lines.append(f"- New Hires: {data.get('newHireCount', '')} joining {data.get('joinDate', '')}")
        comment_lines.append(f"- Available Laptops: {data.get('availableLaptops', '')}")
        if data.get('os') == 'macOS' and data.get('macOsJustification'):
            comment_lines.append(f"- macOS Justification: {data.get('macOsJustification', '')}")
        if comments:
            comment_lines.append(f"- Additional Notes: {comments}")
    else:
        comment_lines.append(f"- Request Type: Replacement")
        comment_lines.append(f"- Persona: {data.get('eucPersona', '')}")
        comment_lines.append(f"- Current Device: {data.get('currentDeviceMake', '')} {data.get('currentDeviceModel', '')}")
        if data.get('currentSerialNumber'):
            comment_lines.append(f"- Serial Number: {data.get('currentSerialNumber')}")
        comment_lines.append(f"- Device Age: {data.get('currentDeviceAge', '')} years")
        if data.get('currentDeviceSpecs'):
            comment_lines.append(f"- Current Specs: {data.get('currentDeviceSpecs')}")
        comment_lines.append(f"- Reason: {data.get('currentCondition', '')}")
        comment_lines.append(f"- Issue Details: {data.get('diagnostics', '')}")
        eus_str = "Yes" if data.get('eusConfirmed') else "No"
        comment_lines.append(f"- EUS/IT Confirmed Unfixable: {eus_str}")
        comment_lines.append(f"- Current Workaround: {data.get('currentWorkaround', '')}")
        if data.get('workaroundDetails'):
            comment_lines.append(f"- Workaround Details: {data.get('workaroundDetails')}")
        if data.get('os') == 'macOS' and data.get('macOsJustification'):
            comment_lines.append(f"- macOS Justification: {data.get('macOsJustification', '')}")
        if data.get('stockNotUsedJustification'):
            comment_lines.append(f"- Why Stock Not Used: {data.get('stockNotUsedJustification')}")
        if comments:
            comment_lines.append(f"- Additional Notes: {comments}")

    detail_comment = "\n".join(comment_lines)

    local_cost_per = data.get('localCostPerDevice', '') or ''
    local_total = ''
    if local_cost_per and isinstance(local_cost_per, (int, float)):
        local_total = local_cost_per * quantity

    today = datetime.now().strftime('%Y-%m-%d')

    row = [
        data.get('eusLeadEmail', ''),
        data.get('buEmail', '') or '',
        data.get('agency', ''),
        today,
        data.get('dateRequired', ''),
        data.get('market', ''),
        device_type_str,
        data.get('laptopModel', ''),
        quantity,
        data.get('localCurrency', '') or '',
        local_cost_per,
        local_total,
        unit_cost,
        unit_cost * quantity,
        rationale,
        data.get('stockOrNewPurchase', ''),
        '',  # Q - review comments (leave empty)
        data.get('etLegalEntity', '') or '',
        data.get('leadEntityInMarket', '') or '',
        data.get('bfcCode', '') or '',
    ]

    return row, detail_comment


def generate_excel_workbook(data_list, request_ids):
    """Generate an Excel workbook with multiple request rows. Returns openpyxl Workbook.

    Args:
        data_list: list of request data dicts
        request_ids: list of request ID strings (same length as data_list)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "APAC Procurement Tracker"

    headers = [
        "Requestor (EUS LEAD) Email ID",
        "Requestor (BU) Email ID",
        "Agency",
        "Date requested",
        "Date Required",
        "Market",
        "Device Type\n(Windows or Mac)",
        "Model\n* PC STD is now Dell Only",
        "Quantity",
        "Local Currency",
        "Cost per Device (Local ccy)",
        "Total Cost (Local Ccy)",
        "Cost per Device (USD)",
        "Total Cost (USD)",
        "Rationale\n(Separate entry for New Joiner or replacement)",
        "Using existing stock or new purchase",
        "SS SC Review Comments\nDate Approved by Regional TechOps Director?",
        "ET Legal Entity Presence in Location?",
        "Lead Entity in Market",
        "BFC Code",
    ]

    header_fill = PatternFill(start_color="0033A0", end_color="0033A0", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True)
        ws.column_dimensions[cell.column_letter].width = max(len(header) + 4, 14)

    # Comments column header (col 23 = W)
    ws.cell(row=1, column=23, value="Comments")
    ws.cell(row=1, column=23).fill = header_fill
    ws.cell(row=1, column=23).font = header_font
    ws.cell(row=1, column=23).alignment = Alignment(wrap_text=True)
    ws.column_dimensions['W'].width = 60

    for row_idx, (data, req_id) in enumerate(zip(data_list, request_ids), 2):
        row_values, detail_comment = _build_excel_row(data)
        for col_idx, value in enumerate(row_values, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
        ws.cell(row=row_idx, column=23, value=detail_comment)
        ws.cell(row=row_idx, column=23).alignment = Alignment(wrap_text=True)

    return wb
```

- [ ] **Step 2: Update server.py to import from utils.py**

Replace the function definitions in `server.py` with imports:
```python
from utils import sanitize_company_name, validate_request, generate_markdown, generate_excel_workbook

# Remove: the function definitions of sanitize_company_name, validate_request,
#          generate_markdown, generate_excel from server.py

# Update generate_filename to import sanitize_company_name from utils
# Update /api/save to use generate_excel_workbook([data], [request_id])
```

The `/api/save` route's Excel generation changes from:
```python
excel_filename = generate_excel(data, request_id)
```
to:
```python
wb = generate_excel_workbook([data], [request_id])
excel_path = os.path.join(APPLICATIONS_DIR, request_id + '.xlsx')
wb.save(excel_path)
excel_filename = request_id + '.xlsx'
```

- [ ] **Step 3: Update test imports**

In `tests/test_server.py`, update imports:
```python
from utils import sanitize_company_name, generate_markdown, validate_request
from server import generate_filename, APPLICATIONS_DIR
```

- [ ] **Step 4: Run all existing tests**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_server.py -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add utils.py server.py tests/test_server.py
git commit -m "refactor: extract shared utils to avoid circular imports"
```

---

### Task 4: Authentication Module

**Files:**
- Create: `auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing tests for auth**

Create `tests/test_auth.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId
import bcrypt


def _make_user(username='testuser', role='user', must_change_password=False):
    pw = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()
    return {
        '_id': ObjectId(),
        'username': username,
        'password_hash': pw,
        'email': 'test@wpp.com',
        'name': 'Test User',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': role,
        'must_change_password': must_change_password,
    }


@pytest.fixture
def auth_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client


def test_login_success(auth_client):
    user = _make_user()
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user
        mock_get_db.return_value = mock_db

        rv = auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert data['user']['username'] == 'testuser'


def test_login_wrong_password(auth_client):
    user = _make_user()
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user
        mock_get_db.return_value = mock_db

        rv = auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
    assert rv.status_code == 401


def test_login_user_not_found(auth_client):
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = None
        mock_get_db.return_value = mock_db

        rv = auth_client.post('/api/login', json={
            'username': 'nobody',
            'password': 'password123'
        })
    assert rv.status_code == 401


def test_me_unauthenticated(auth_client):
    rv = auth_client.get('/api/me')
    assert rv.status_code == 401


def test_logout(auth_client):
    rv = auth_client.post('/api/logout')
    assert rv.status_code == 200


def test_change_password(auth_client):
    user = _make_user(must_change_password=True)
    # Login first
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user
        mock_get_db.return_value = mock_db
        auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })

    # Change password
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user
        mock_db.users.update_one = MagicMock()
        mock_get_db.return_value = mock_db
        rv = auth_client.post('/api/change-password', json={
            'old_password': 'password123',
            'new_password': 'newpass123'
        })
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True


def test_change_password_too_short(auth_client):
    user = _make_user()
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user
        mock_get_db.return_value = mock_db
        auth_client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })

    rv = auth_client.post('/api/change-password', json={
        'old_password': 'password123',
        'new_password': 'ab'
    })
    assert rv.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_auth.py -v`
Expected: FAIL

- [ ] **Step 3: Implement auth.py**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add auth.py tests/test_auth.py
git commit -m "feat: add authentication module with login/logout/change-password"
```

---

### Task 5: User Management API (Admin Only)

**Files:**
- Create: `api_users.py`
- Create: `tests/test_api_users.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api_users.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId
import bcrypt


def _make_user_doc(username='testuser', role='user'):
    pw = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()
    return {
        '_id': ObjectId(),
        'username': username,
        'password_hash': pw,
        'email': f'{username}@wpp.com',
        'name': 'Test User',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': role,
        'must_change_password': False,
    }


@pytest.fixture
def admin_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        admin_doc = _make_user_doc('admin', 'admin')
        with patch('auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.users.find_one.return_value = admin_doc
            mock_get_db.return_value = mock_db
            client.post('/api/login', json={'username': 'admin', 'password': 'password123'})
        yield client


def test_list_users_as_admin(admin_client):
    users = [_make_user_doc('user1'), _make_user_doc('user2')]
    with patch('api_users.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find.return_value = users
        mock_get_db.return_value = mock_db

        rv = admin_client.get('/api/users')
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data['users']) == 2


def test_create_user_as_admin(admin_client):
    with patch('api_users.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_get_db.return_value = mock_db

        rv = admin_client.post('/api/users', json={
            'username': 'newuser',
            'password': 'pass123',
            'email': 'new@wpp.com',
            'name': 'New User',
            'opco': 'VML',
            'market': 'Shanghai',
            'role': 'user'
        })
    assert rv.status_code == 201
    data = rv.get_json()
    assert data['success'] is True


def test_create_user_duplicate_username(admin_client):
    with patch('api_users.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = _make_user_doc('existing')
        mock_get_db.return_value = mock_db

        rv = admin_client.post('/api/users', json={
            'username': 'existing',
            'password': 'pass123',
            'email': 'e@wpp.com',
            'name': 'E',
            'opco': 'VML',
            'market': 'Shanghai',
            'role': 'user'
        })
    assert rv.status_code == 400


def test_non_admin_cannot_list_users(auth_client):
    """Regular users should get 403 when accessing admin endpoints."""
    user_doc = _make_user_doc('regular', 'user')
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user_doc
        mock_get_db.return_value = mock_db
        auth_client.post('/api/login', json={'username': 'regular', 'password': 'password123'})

    rv = auth_client.get('/api/users')
    assert rv.status_code == 403


@pytest.fixture
def auth_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_api_users.py -v`
Expected: FAIL

- [ ] **Step 3: Implement api_users.py**

```python
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
    users = list(db.users.find({}, {'password_hash': 0}))
    return jsonify({'success': True, 'users': [_user_to_dict(u) for u in users]})


@users_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    required = ['username', 'password', 'email', 'name', 'opco', 'market', 'role']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'success': False, 'error': f'{field} is required'}), 400

    if data['role'] not in ('admin', 'user'):
        return jsonify({'success': False, 'error': 'role must be admin or user'}), 400

    db = get_db()
    if db.users.find_one({'username': data['username']}):
        return jsonify({'success': False, 'error': 'Username already exists'}), 400

    now = datetime.now(timezone.utc)
    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    user_doc = {
        'username': data['username'].strip(),
        'password_hash': password_hash,
        'email': data['email'].strip(),
        'name': data['name'].strip(),
        'opco': data['opco'].strip(),
        'market': data['market'].strip(),
        'role': data['role'],
        'must_change_password': True,
        'created_at': now,
        'updated_at': now,
    }
    result = db.users.insert_one(user_doc)
    user_doc['_id'] = result.inserted_id
    return jsonify({'success': True, 'user': _user_to_dict(user_doc)}), 201


@users_bp.route('/api/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    db = get_db()
    user_doc = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_doc:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    update_fields = {}
    for field in ['email', 'name', 'opco', 'market', 'role']:
        if field in data and data[field]:
            update_fields[field] = data[field].strip()

    if 'password' in data and data['password']:
        update_fields['password_hash'] = bcrypt.hashpw(
            data['password'].encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    if update_fields:
        update_fields['updated_at'] = datetime.now(timezone.utc)
        db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_fields})

    updated = db.users.find_one({'_id': ObjectId(user_id)})
    return jsonify({'success': True, 'user': _user_to_dict(updated)})


@users_bp.route('/api/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    db = get_db()
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete yourself'}), 400

    result = db.users.delete_one({'_id': ObjectId(user_id)})
    if result.deleted_count == 0:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    return jsonify({'success': True})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_api_users.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api_users.py tests/test_api_users.py
git commit -m "feat: add user management API with admin-only CRUD"
```

---

### Task 6: Application CRUD API + Batch Export

**Files:**
- Create: `api_applications.py`
- Create: `tests/test_api_applications.py`

**Important:** The `/api/applications/export` route MUST be registered before `/api/applications/<app_id>` to prevent Flask from matching "export" as an app_id. The application includes a `status` field per the spec.

- [ ] **Step 1: Write failing tests**

Create `tests/test_api_applications.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId
import bcrypt


VALID_APP_DATA = {
    "requestType": "new",
    "requestorName": "Test User",
    "agency": "VML",
    "market": "Shanghai",
    "email": "test@wpp.com",
    "staffCategory": "Standard",
    "stockNoBuffer": True,
    "stockListingUpToDate": True,
    "eucPersona": "Standard User",
    "eucStandardsVersion": "2025/Q4",
    "laptopModel": "Dell Latitude 5550",
    "os": "Windows",
    "quantity": 1,
    "specs": "16GB RAM, 512GB SSD",
    "unitCost": 1200,
    "currency": "USD",
    "costFromDell": True,
    "costExcludesTax": True,
    "newHireCount": 1,
    "joinDate": "2026-05-01",
    "availableLaptops": "None",
    "comments": "",
}


def _make_user_doc(role='user'):
    pw = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()
    return {
        '_id': ObjectId(),
        'username': 'testuser',
        'password_hash': pw,
        'email': 'test@wpp.com',
        'name': 'Test User',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': role,
        'must_change_password': False,
    }


@pytest.fixture
def user_client():
    from server import app
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        user_doc = _make_user_doc('user')
        with patch('auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.users.find_one.return_value = user_doc
            mock_get_db.return_value = mock_db
            client.post('/api/login', json={'username': 'testuser', 'password': 'password123'})
        yield client, user_doc


def test_create_application(user_client):
    client, user_doc = user_client
    with patch('api_applications.get_db') as mock_get_db, \
         patch('api_applications.generate_request_id', return_value='REQ-2026-03-20-001-VML'):
        mock_db = MagicMock()
        mock_db.applications.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_get_db.return_value = mock_db

        rv = client.post('/api/applications', json=VALID_APP_DATA)
    assert rv.status_code == 201
    data = rv.get_json()
    assert data['success'] is True
    assert data['request_id'] == 'REQ-2026-03-20-001-VML'


def test_list_own_applications(user_client):
    client, user_doc = user_client
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    apps = [{
        '_id': ObjectId(),
        'request_id': 'REQ-2026-03-20-001-VML',
        'user_id': user_doc['_id'],
        'status': 'submitted',
        'data': VALID_APP_DATA,
        'created_at': now,
        'updated_at': now,
    }]
    with patch('api_applications.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = apps
        mock_db.applications.find.return_value = mock_cursor
        mock_get_db.return_value = mock_db

        rv = client.get('/api/applications')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert len(data['applications']) == 1


def test_delete_own_application(user_client):
    client, user_doc = user_client
    app_id = ObjectId()
    app_doc = {
        '_id': app_id,
        'user_id': user_doc['_id'],
        'request_id': 'REQ-2026-03-20-001-VML',
        'status': 'submitted',
        'data': VALID_APP_DATA,
    }
    with patch('api_applications.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.applications.find_one.return_value = app_doc
        mock_db.applications.delete_one.return_value = MagicMock(deleted_count=1)
        mock_get_db.return_value = mock_db

        rv = client.delete(f'/api/applications/{app_id}')
    assert rv.status_code == 200


def test_cannot_delete_others_application(user_client):
    client, user_doc = user_client
    app_id = ObjectId()
    other_user_id = ObjectId()  # different user
    app_doc = {
        '_id': app_id,
        'user_id': other_user_id,
        'request_id': 'REQ-2026-03-20-001-VML',
        'status': 'submitted',
        'data': VALID_APP_DATA,
    }
    with patch('api_applications.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.applications.find_one.return_value = app_doc
        mock_get_db.return_value = mock_db

        rv = client.delete(f'/api/applications/{app_id}')
    assert rv.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_api_applications.py -v`
Expected: FAIL

- [ ] **Step 3: Implement api_applications.py**

```python
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


# IMPORTANT: /export must be registered BEFORE /<app_id> to avoid Flask
# matching "export" as an app_id parameter.

@applications_bp.route('/api/applications/export', methods=['GET'])
@login_required
def export_applications():
    db = get_db()
    query = {} if current_user.is_admin else {'user_id': ObjectId(current_user.id)}
    apps = list(db.applications.find(query).sort('created_at', -1))

    if not apps:
        return jsonify({'success': False, 'error': 'No applications to export'}), 404

    wb = generate_excel_workbook(
        [a['data'] for a in apps],
        [a['request_id'] for a in apps]
    )
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"laptop-requests-export-{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@applications_bp.route('/api/applications', methods=['GET'])
@login_required
def list_applications():
    db = get_db()
    query = {} if current_user.is_admin else {'user_id': ObjectId(current_user.id)}
    apps = list(db.applications.find(query).sort('created_at', -1))
    return jsonify({'success': True, 'applications': [_app_to_dict(a) for a in apps]})


@applications_bp.route('/api/applications', methods=['POST'])
@login_required
def create_application():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

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
    db.applications.insert_one(app_doc)

    return jsonify({'success': True, 'request_id': request_id, 'id': str(app_doc['_id'])}), 201


@applications_bp.route('/api/applications/<app_id>', methods=['GET'])
@login_required
def get_application(app_id):
    db = get_db()
    app_doc = db.applications.find_one({'_id': ObjectId(app_id)})
    if not app_doc:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if not current_user.is_admin and str(app_doc['user_id']) != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    return jsonify({'success': True, 'application': _app_to_dict(app_doc)})


@applications_bp.route('/api/applications/<app_id>', methods=['PUT'])
@login_required
def update_application(app_id):
    db = get_db()
    app_doc = db.applications.find_one({'_id': ObjectId(app_id)})
    if not app_doc:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if not current_user.is_admin and str(app_doc['user_id']) != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    errors = validate_request(data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400

    db.applications.update_one(
        {'_id': ObjectId(app_id)},
        {'$set': {'data': data, 'updated_at': datetime.now(timezone.utc)}}
    )
    updated = db.applications.find_one({'_id': ObjectId(app_id)})
    return jsonify({'success': True, 'application': _app_to_dict(updated)})


@applications_bp.route('/api/applications/<app_id>', methods=['DELETE'])
@login_required
def delete_application(app_id):
    db = get_db()
    app_doc = db.applications.find_one({'_id': ObjectId(app_id)})
    if not app_doc:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if not current_user.is_admin and str(app_doc['user_id']) != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    db.applications.delete_one({'_id': ObjectId(app_id)})
    return jsonify({'success': True})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/test_api_applications.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api_applications.py tests/test_api_applications.py
git commit -m "feat: add application CRUD API with batch export"
```

---

### Task 7: Integrate Blueprints into server.py

**Files:**
- Modify: `server.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_server.py`

- [ ] **Step 1: Rewrite server.py to register blueprints**

The new `server.py` should:
1. Import from `utils.py` instead of defining functions locally
2. Register auth, users, applications blueprints
3. Add routes for `/login` and `/dashboard` pages
4. Keep `/api/save` as a backward-compatible alias that requires login
5. Call `init_db()` on startup
6. Keep `/api/health` (no auth required)
7. Keep `generate_filename()` locally (it uses filesystem, only needed for legacy `/api/save`)

```python
import os
import re
import glob
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_login import login_required, current_user

from utils import validate_request, generate_markdown, generate_excel_workbook, sanitize_company_name
from auth import auth_bp, init_login
from api_users import users_bp
from api_applications import applications_bp
from db import init_db

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


@app.route('/login')
def login_page():
    return send_from_directory(STATIC_DIR, 'login.html')


@app.route('/dashboard')
def dashboard_page():
    return send_from_directory(STATIC_DIR, 'dashboard.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/save', methods=['POST'])
@login_required
def save_request():
    """Legacy endpoint — delegates to applications API."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided', 'details': []}), 400

    errors = validate_request(data)
    if errors:
        return jsonify({'success': False, 'error': 'Validation failed', 'details': errors}), 400

    # Save to MongoDB via applications API logic
    from api_applications import generate_request_id
    from bson import ObjectId
    from datetime import timezone
    from db import get_db

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
    db.applications.insert_one(app_doc)

    return jsonify({
        'success': True,
        'request_id': request_id,
        'id': str(app_doc['_id']),
    })


@app.route('/applications/<path:filename>')
def download_file(filename):
    return send_from_directory(APPLICATIONS_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8900, debug=True)
```

- [ ] **Step 2: Update tests/conftest.py**

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from server import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret'
    with flask_app.test_client() as client:
        yield client
```

- [ ] **Step 3: Update tests/test_server.py for new imports and auth**

Update imports at the top of `test_server.py`:
```python
from utils import sanitize_company_name, generate_markdown
from server import generate_filename
```

The `/api/save` tests now require authentication. Update them to either:
- Mock login before calling `/api/save`, OR
- Test validation logic directly via `validate_request()` from utils (preferred for unit tests)

For the integration tests (`test_save_*`), add a login helper:
```python
from unittest.mock import patch, MagicMock
from bson import ObjectId
import bcrypt

def _login_test_user(client):
    pw = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()
    user_doc = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password_hash': pw,
        'email': 'test@wpp.com',
        'name': 'Test',
        'opco': 'VML',
        'market': 'Shanghai',
        'role': 'user',
        'must_change_password': False,
    }
    with patch('auth.get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.users.find_one.return_value = user_doc
        mock_get_db.return_value = mock_db
        client.post('/api/login', json={'username': 'testuser', 'password': 'password123'})
    return user_doc
```

Then update each `test_save_*` test to call `_login_test_user(client)` before the POST, and mock `api_applications.get_db` and `db.get_db` for the MongoDB calls.

- [ ] **Step 4: Run all tests**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add server.py tests/conftest.py tests/test_server.py
git commit -m "feat: integrate auth, users, applications blueprints into server"
```

---

### Task 8: Login Page

**Files:**
- Create: `static/login.html`

- [ ] **Step 1: Create login.html**

Full single-file HTML page with embedded CSS and JS:
- WPP branding (#0033A0 header)
- Centered login card with username + password fields
- Submit button, error message display
- On success: if `must_change_password` is true, show change-password modal; otherwise redirect to `/dashboard`
- Change-password modal: old password (hidden, prefilled with login password), new password, confirm new password
- POST to `/api/login`, then optionally POST to `/api/change-password`

Key JS logic:
```javascript
var loginPassword = '';

async function login(e) {
    e.preventDefault();
    var username = document.getElementById('username').value;
    var password = document.getElementById('password').value;
    loginPassword = password;

    var res = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username: username, password: password })
    });
    var data = await res.json();
    if (data.success) {
        if (data.user.must_change_password) {
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('changePasswordForm').style.display = 'block';
        } else {
            window.location.href = '/dashboard';
        }
    } else {
        document.getElementById('error').textContent = data.error;
        document.getElementById('error').style.display = 'block';
    }
}

async function changePassword(e) {
    e.preventDefault();
    var newPass = document.getElementById('newPassword').value;
    var confirmPass = document.getElementById('confirmPassword').value;

    if (newPass !== confirmPass) {
        document.getElementById('cpError').textContent = 'Passwords do not match';
        document.getElementById('cpError').style.display = 'block';
        return;
    }
    if (newPass.length < 6) {
        document.getElementById('cpError').textContent = 'Password must be at least 6 characters';
        document.getElementById('cpError').style.display = 'block';
        return;
    }

    var res = await fetch('/api/change-password', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ old_password: loginPassword, new_password: newPass })
    });
    var data = await res.json();
    if (data.success) {
        window.location.href = '/dashboard';
    } else {
        document.getElementById('cpError').textContent = data.error;
        document.getElementById('cpError').style.display = 'block';
    }
}
```

- [ ] **Step 2: Verify login page renders**

Start server, visit `http://localhost:8900/login` — verify the page renders with WPP styling.

- [ ] **Step 3: Commit**

```bash
git add static/login.html
git commit -m "feat: add login page with change-password flow"
```

---

### Task 9: Dashboard Page

**Files:**
- Create: `static/dashboard.html`

- [ ] **Step 1: Create dashboard.html**

Full single-file HTML with embedded CSS and JS. Layout:

**Left sidebar (240px, dark background):**
- WPP logo/title at top
- Navigation items with icons (use Unicode/text icons):
  - "My Applications" (default active)
  - "New Application" (links to `/` wizard)
  - (Admin only) "All Applications"
  - (Admin only) "User Management"
  - "Change Password"
- Logged-in user info at bottom (name, role)
- Logout button

**Right content area:**
- Dynamic content based on selected nav item, rendered by JS functions

**"My Applications" view:**
- "Batch Export" button at top-right
- Table columns: Request ID, OpCo, Device Model, Quantity, Date, Actions
- Action buttons: View, Edit, Delete
- View opens a modal showing all application data fields (read-only)
- Edit navigates to `/?edit=<app_id>`
- Delete shows `confirm()` dialog, then calls `DELETE /api/applications/:id`, reloads list

**"All Applications" view (admin only):**
- Same as "My Applications" but shows all users' applications
- Additional column: Submitted By
- Filter/search bar at top

**"User Management" view (admin only):**
- "Add User" button at top-right, opens modal form
- Table columns: Username, Name, Email, OpCo, Market, Role, Actions
- Edit button opens modal with prefilled data
- Delete button with `confirm()` dialog
- Modal form fields: username, password (required on create, optional on edit), email, name, OpCo (dropdown matching wizard options), Market (dropdown matching wizard options), Role (admin/user)

**"Change Password" view:**
- Simple form card: current password, new password, confirm password
- POST to `/api/change-password`
- Show success/error message

Key JS structure:
```javascript
var currentUser = null;
var currentView = 'my-applications';

async function init() {
    var res = await fetch('/api/me');
    if (!res.ok) { window.location.href = '/login'; return; }
    var data = await res.json();
    currentUser = data.user;
    renderSidebar();
    showView('my-applications');
}

function renderSidebar() {
    // Build nav items, show admin items only if currentUser.role === 'admin'
}

function showView(view) {
    currentView = view;
    // Update active nav item styling
    if (view === 'my-applications') loadMyApplications();
    else if (view === 'all-applications') loadAllApplications();
    else if (view === 'user-management') loadUsers();
    else if (view === 'change-password') showChangePasswordForm();
}

async function loadMyApplications() {
    var res = await fetch('/api/applications');
    var data = await res.json();
    renderApplicationsTable(data.applications, false);
}

async function loadAllApplications() {
    var res = await fetch('/api/applications');
    var data = await res.json();
    renderApplicationsTable(data.applications, true);
}

function renderApplicationsTable(apps, showUser) {
    // Build HTML table with action buttons
}

async function deleteApplication(id) {
    if (!confirm('Are you sure you want to delete this application?')) return;
    await fetch('/api/applications/' + id, { method: 'DELETE' });
    showView(currentView);  // reload
}

function editApplication(id) {
    window.location.href = '/?edit=' + id;
}

function exportAll() {
    window.location.href = '/api/applications/export';
}

async function loadUsers() {
    var res = await fetch('/api/users');
    var data = await res.json();
    renderUsersTable(data.users);
}

// User CRUD modals...
async function saveUser(formData, userId) {
    var url = userId ? '/api/users/' + userId : '/api/users';
    var method = userId ? 'PUT' : 'POST';
    var res = await fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    });
    // handle response, close modal, reload list
}

async function deleteUser(id) {
    if (!confirm('Are you sure?')) return;
    await fetch('/api/users/' + id, { method: 'DELETE' });
    loadUsers();
}

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login';
}

window.addEventListener('DOMContentLoaded', init);
```

- [ ] **Step 2: Verify dashboard renders**

Start server, login as admin, verify:
- Sidebar shows all nav items including admin-only ones
- My Applications table loads (empty initially)
- User Management loads with the admin user
- All navigation works

- [ ] **Step 3: Commit**

```bash
git add static/dashboard.html
git commit -m "feat: add dashboard with application list and user management"
```

---

### Task 10: Modify Wizard (index.html) for Auth + Edit Mode

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Add auth guard and user profile auto-fill**

At the beginning of the `<script>` section in index.html, add:
```javascript
var currentUser = null;
var editingAppId = null;

// Auth guard — check login, auto-fill profile, check edit mode
fetch('/api/me').then(function(r) {
    if (!r.ok) { window.location.href = '/login'; return Promise.reject('not authed'); }
    return r.json();
}).then(function(data) {
    currentUser = data.user;
    // Auto-fill from user profile
    document.getElementById('requestorName').value = currentUser.name;
    document.getElementById('email').value = currentUser.email;
    var agencySelect = document.getElementById('agency');
    if (agencySelect) agencySelect.value = currentUser.opco;
    var marketSelect = document.getElementById('market');
    if (marketSelect) marketSelect.value = currentUser.market;
    // Check edit mode
    var params = new URLSearchParams(window.location.search);
    var editId = params.get('edit');
    if (editId) {
        editingAppId = editId;
        loadApplicationForEdit(editId);
    }
}).catch(function() {});
```

- [ ] **Step 2: Implement loadApplicationForEdit()**

This function fetches application data and populates ALL form fields:
```javascript
function loadApplicationForEdit(appId) {
    fetch('/api/applications/' + appId)
        .then(function(r) { return r.json(); })
        .then(function(result) {
            if (!result.success) return;
            var d = result.application.data;

            // Step 1: Request type
            var rtRadio = document.querySelector('input[name="requestType"][value="' + d.requestType + '"]');
            if (rtRadio) { rtRadio.checked = true; rtRadio.dispatchEvent(new Event('change', {bubbles: true})); }

            // Step 2: Requestor info
            document.getElementById('requestorName').value = d.requestorName || '';
            document.getElementById('agency').value = d.agency || '';
            document.getElementById('market').value = d.market || '';
            document.getElementById('email').value = d.email || '';
            if (d.buEmail) document.getElementById('buEmail').value = d.buEmail;
            if (d.cityLeader) document.getElementById('cityLeader').value = d.cityLeader;
            if (d.eusLeadEmail) {
                var cl = document.getElementById('cityLeader');
                if (cl) cl.value = d.eusLeadEmail;
            }
            if (d.dateRequired) document.getElementById('dateRequired').value = d.dateRequired;
            if (d.staffCategory) document.getElementById('staffCategory').value = d.staffCategory;

            // Step 3: Stock verification
            document.getElementById('stockNoBuffer').checked = !!d.stockNoBuffer;
            document.getElementById('stockListingUpToDate').checked = !!d.stockListingUpToDate;

            // Step 4: Laptop specs
            if (d.eucPersona) {
                document.getElementById('eucPersona').value = d.eucPersona;
                document.getElementById('eucPersona').dispatchEvent(new Event('change'));
            }
            if (d.deviceType) {
                var dtRadio = document.querySelector('input[name="deviceType"][value="' + d.deviceType + '"]');
                if (dtRadio) { dtRadio.checked = true; dtRadio.dispatchEvent(new Event('change', {bubbles: true})); }
            }
            // Device selection needs to happen after cards render
            setTimeout(function() {
                // Find and select the matching device by model name
                var cards = document.querySelectorAll('.device-card');
                cards.forEach(function(card, idx) {
                    if (card.querySelector('.device-name') &&
                        card.querySelector('.device-name').textContent === d.laptopModel) {
                        selectDevice(idx);
                    }
                });
                if (d.quantity) document.getElementById('quantity').value = d.quantity;
                if (d.specs) document.getElementById('specs').value = d.specs;
                if (d.macOsJustification) document.getElementById('macOsJustification').value = d.macOsJustification;
            }, 500);

            // Step 5: Cost & Sourcing
            if (d.localCurrency) document.getElementById('localCurrency').value = d.localCurrency;
            if (d.exchangeRate) document.getElementById('exchangeRate').value = d.exchangeRate;
            if (d.localCostPerDevice) document.getElementById('localCostPerDevice').value = d.localCostPerDevice;
            document.getElementById('costFromDell').checked = !!d.costFromDell;
            document.getElementById('costExcludesTax').checked = !!d.costExcludesTax;

            // Step 6: New hire details (if applicable)
            if (d.requestType === 'new') {
                if (d.newHireCount) document.getElementById('newHireCount').value = d.newHireCount;
                if (d.joinDate) document.getElementById('joinDate').value = d.joinDate;
                if (d.availableLaptops) document.getElementById('availableLaptops').value = d.availableLaptops;
            }

            // Step 7: Replacement details (if applicable)
            if (d.requestType === 'replacement') {
                if (d.currentDeviceMake) document.getElementById('currentDeviceMake').value = d.currentDeviceMake;
                if (d.currentDeviceModel) document.getElementById('currentDeviceModel').value = d.currentDeviceModel;
                if (d.currentSerialNumber) document.getElementById('currentSerialNumber').value = d.currentSerialNumber;
                if (d.currentDeviceAge) document.getElementById('currentDeviceAge').value = d.currentDeviceAge;
                if (d.currentDeviceSpecs) document.getElementById('currentDeviceSpecs').value = d.currentDeviceSpecs;
                if (d.currentCondition) document.getElementById('currentCondition').value = d.currentCondition;
                if (d.diagnostics) document.getElementById('diagnostics').value = d.diagnostics;
                document.getElementById('eusConfirmed').checked = !!d.eusConfirmed;
                if (d.currentWorkaround) document.getElementById('currentWorkaround').value = d.currentWorkaround;
                if (d.workaroundDetails) document.getElementById('workaroundDetails').value = d.workaroundDetails;
                if (d.stockNotUsedJustification) document.getElementById('stockNotUsedJustification').value = d.stockNotUsedJustification;
            }

            // Step 8: Procurement
            if (d.etLegalEntity) document.getElementById('etLegalEntity').value = d.etLegalEntity;
            if (d.leadEntityInMarket) document.getElementById('leadEntityInMarket').value = d.leadEntityInMarket;
            if (d.bfcCode) document.getElementById('bfcCode').value = d.bfcCode;
            if (d.stockOrNewPurchase) document.getElementById('stockOrNewPurchase').value = d.stockOrNewPurchase;
            if (d.transferEntity) document.getElementById('transferEntity').value = d.transferEntity;
            if (d.comments) document.getElementById('comments').value = d.comments;
        });
}
```

- [ ] **Step 3: Modify submitRequest() to use new API**

Replace the existing `submitRequest()` function body:
```javascript
function submitRequest() {
    var data = collectData();
    var url = editingAppId ? '/api/applications/' + editingAppId : '/api/applications';
    var method = editingAppId ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(function(r) { return r.json(); })
      .then(function(result) {
          if (result.success) {
              window.location.href = '/dashboard';
          } else {
              var msg = result.error || 'Submission failed';
              if (result.details) msg += ': ' + result.details.join(', ');
              alert(msg);
          }
      })
      .catch(function(err) {
          alert('Network error: ' + err.message);
      });
}
```

- [ ] **Step 4: Add "Back to Dashboard" link in header**

In the `.header-inner` section of index.html, add:
```html
<a href="/dashboard" style="color: #fff; opacity: 0.8; text-decoration: none; font-size: 0.85rem;">&larr; Back to Dashboard</a>
```

- [ ] **Step 5: Test the full flow manually**

1. Visit `/` — should redirect to `/login`
2. Login as admin/admin123 — should force password change
3. After password change — redirected to `/dashboard`
4. Click "New Application" — wizard opens with pre-filled fields
5. Submit — returns to dashboard, application visible in list
6. Click edit on the application — wizard opens with all fields populated
7. Modify and submit — returns to dashboard with updated data
8. Delete — application removed
9. Export — downloads Excel file

- [ ] **Step 6: Commit**

```bash
git add static/index.html
git commit -m "feat: add auth guard and edit mode to wizard"
```

---

### Task 11: Cleanup and End-to-End Verification

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update .gitignore**

Add:
```
docker-compose.override.yml
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/chunyuanlu/WebApp/wpp-work/Application && source venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Full end-to-end manual test**

1. `docker compose up -d` — MongoDB starts
2. `./start.sh` — Flask starts, console shows `[INIT] Default admin created: admin / admin123`
3. Browser: `/login` → login admin/admin123 → forced password change → `/dashboard`
4. Dashboard: User Management → create user (username: testuser, VML, Shanghai, user role)
5. Logout → login as testuser → forced password change
6. New Application → fill wizard → submit → appears in My Applications
7. View application (modal) → verify all fields
8. Edit application → modify quantity → submit → verify update in list
9. Delete application → confirm → gone from list
10. Export → downloads Excel with the application data
11. Login as admin → All Applications shows testuser's requests
12. Admin can edit/delete any application

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: update gitignore for Docker"
```

---

## Summary of Tasks

| Task | Description | Dependencies |
|------|-------------|-------------|
| 1 | Docker + MongoDB setup | None |
| 2 | Database connection and initialization | Task 1 |
| 3 | Extract shared utilities to utils.py | None |
| 4 | Authentication module | Tasks 2, 3 |
| 5 | User management API (admin only) | Task 4 |
| 6 | Application CRUD API + batch export | Tasks 3, 4 |
| 7 | Integrate blueprints into server.py | Tasks 4, 5, 6 |
| 8 | Login page | Task 7 |
| 9 | Dashboard page | Task 7 |
| 10 | Modify wizard for auth + edit mode | Task 7 |
| 11 | Cleanup and end-to-end verification | Tasks 8, 9, 10 |
