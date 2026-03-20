# WPP Laptop Request System — Design Spec

## Overview

A web-based wizard form for submitting laptop requests (new and replacement) following WPP procurement process requirements. Generates structured Markdown records saved to `/applications/`.

## Architecture

- **Frontend:** Single vanilla HTML file (`static/index.html`) with embedded CSS and JS
- **Backend:** Python Flask server (`server.py`) running on port 8900 inside a venv
- **Storage:** Markdown files written to `/applications/` directory

### Project Structure

```
Application/
├── server.py              # Flask server (port 8900)
├── requirements.txt       # Flask dependency
├── venv/                  # Python virtual environment
├── static/
│   └── index.html         # Wizard form (single file, embedded CSS/JS)
└── applications/          # Generated MD files
    ├── REQ-2026-03-19-001-VML-Shanghai.md
    └── ...
```

## Visual Style

Corporate WPP brand identity:
- Primary accent: navy blue `#0033A0`
- Clean white form backgrounds
- Professional typography
- Progress bar showing current step
- Responsive layout

## Wizard Steps

### Step 1 — Request Type
- Radio selection: **New Laptop** or **Replacement Laptop**
- Determines which conditional steps appear (Step 6 or Step 7)

### Step 2 — Requestor Info
- Name (text, required)
- Agency / Company (text, required)
- Market (text, required)
- Email (email, required)
- Staff category (dropdown: Standard, WPP ET Staff, India HQ — used to enforce stricter macOS justification)

### Step 3 — Stock Verification
- Checkbox: "I confirm all existing stocks within markets do not have buffer or almost-new laptops"
- Checkbox: "I confirm the laptop count from ALL agencies within market in 2026 Stock listing file is up to date"
- Both required to proceed

### Step 4 — Laptop Specs & Persona
- WPP EUC Standards Persona (dropdown: Standard User, Power User, Developer, Senior Leader, Other)
- EUC Standards version (read-only, displays "2025/Q4" — recorded in output for audit trail)
- Laptop model (text, required)
- Operating system (dropdown: Windows, macOS)
- If macOS selected: Justification for macOS vs Windows (textarea, required). Additional note shown if staff category = WPP ET Staff or India HQ: "Stricter justification required for WPP ET / India HQ staff"
- Quantity (number, required, min 1)
- Specs summary (textarea — RAM, storage, processor, etc.)

**Non-standard configuration** is defined as: EUC Persona = "Other", or specs/model deviating from the WPP EUC Standards for the selected persona.

### Step 5 — Cost & Sourcing
- Unit cost (number, required)
- Currency (dropdown: USD, EUR, GBP, CNY, INR, SGD, AUD, BRL, required)
- Total cost (auto-calculated: unit cost × quantity, displayed read-only)
- Checkbox: "I confirm cost is from Dell Direct portal / Dell-approved partner in market"
- Checkbox: "I confirm cost excludes local taxes"

### Step 6 — New Hire Details (only if Step 1 = New Laptop)
- Number of new hires (number, required)
- Expected join date (date, required)
- New hire's WPP EUC Persona override (dropdown, optional — only needed if new hires require a different persona than Step 4 selection)
- Textarea: "Are there available functional laptops?" (required — indicate if none available)

### Step 7 — Replacement Details (only if Step 1 = Replacement Laptop)
- Current laptop condition (dropdown: Poor, Non-functional, Damaged, Outdated)
- Diagnostics performed to date (textarea, required)
- Checkbox: "EUS team has confirmed this laptop cannot be fixed"
- If existing stock could be used instead: Justification for why not (textarea — especially for Senior Leader requests)
- If non-standard config: Justification (textarea, required when EUC Persona = Other or specs deviate)

### Step 8 — Additional Comments (optional)
- Additional comments or notes for the approver (textarea, optional)

### Step 9 — Review & Submit
- Read-only summary of all fields grouped by step
- Edit button per section to jump back to that step
- Submit button: POST to `/api/save`, writes MD file to `/applications/`
- Success message with filename shown after save

## File Naming Convention

```
REQ-YYYY-MM-DD-SEQ-CompanyName.md
```

- `REQ` — fixed prefix
- `YYYY-MM-DD` — submission date
- `SEQ` — 3-digit zero-padded sequence number, auto-incremented per day
- `CompanyName` — from the Agency/Company field, sanitized (non-alphanumeric chars replaced with hyphens, consecutive hyphens collapsed, leading/trailing hyphens trimmed)

Example: `REQ-2026-03-19-001-VML-Shanghai.md`

### Sequence Logic

On save, the server scans `/applications/` for files matching `REQ-{today's date}-*`, extracts the highest sequence number, and increments by 1. Starts at 001 if none exist for the day.

## Generated MD File Format

```markdown
# Laptop Request — REQ-2026-03-19-001-VML-Shanghai

**Generated:** 2026-03-19 15:30:00
**Request ID:** REQ-2026-03-19-001-VML-Shanghai

## Request Type
- Type: New Laptop

## Requestor Information
- Name: John Doe
- Agency/Company: VML Shanghai
- Market: China
- Email: john.doe@vml.com
- Staff Category: Standard

## Stock Verification
- [x] No buffer or almost-new laptops in existing stock
- [x] 2026 Stock listing file is up to date

## Laptop Specifications
- EUC Persona: Standard User
- EUC Standards Version: 2025/Q4
- Model: Dell Latitude 5550
- OS: Windows
- macOS Justification: N/A
- Quantity: 3
- Specs: 16GB RAM, 512GB SSD, Intel Core i5

## Cost & Sourcing
- Unit Cost: 1,200 USD
- Total Cost: 3,600 USD
- [x] Cost from Dell Direct portal / approved partner
- [x] Cost excludes local taxes

## New Hire Details
- Number of New Hires: 3
- Expected Join Date: 2026-04-15
- EUC Persona: Standard User
- Available Functional Laptops: No functional laptops available in current stock

## Additional Comments
(none)
```

## API Endpoint

### POST /api/save

**Request body (JSON):**
```json
{
  "requestType": "new",
  "requestorName": "John Doe",
  "agency": "VML Shanghai",
  "market": "China",
  "email": "john.doe@vml.com",
  "staffCategory": "Standard",
  "stockNoBuffer": true,
  "stockListingUpToDate": true,
  "eucPersona": "Standard User",
  "eucStandardsVersion": "2025/Q4",
  "laptopModel": "Dell Latitude 5550",
  "os": "Windows",
  "macOsJustification": null,
  "quantity": 3,
  "specs": "16GB RAM, 512GB SSD, Intel Core i5",
  "unitCost": 1200,
  "currency": "USD",
  "costFromDell": true,
  "costExcludesTax": true,
  "newHireCount": 3,
  "joinDate": "2026-04-15",
  "newHirePersona": "Standard User",
  "availableLaptops": "No functional laptops available",
  "currentCondition": null,
  "diagnostics": null,
  "eusConfirmed": null,
  "stockNotUsedJustification": null,
  "nonStandardJustification": null,
  "comments": ""
}
```

**Response — success (JSON):**
```json
{
  "success": true,
  "filename": "REQ-2026-03-19-001-VML-Shanghai.md",
  "path": "applications/REQ-2026-03-19-001-VML-Shanghai.md"
}
```

**Response — error (JSON):**
```json
{
  "success": false,
  "error": "Validation failed",
  "details": ["requestorName is required", "email format invalid"]
}
```

**Server-side validation:** The server re-validates all required fields before writing the MD file. Client-side validation is for UX only; the server is the source of truth.

## Validation Rules

Each step validates before allowing the user to proceed to the next step:
- Required text fields must be non-empty
- Email must be valid format
- Numeric fields must be positive
- Checkboxes for stock verification and cost confirmation are mandatory
- Conditional fields (Steps 6/7) only validated when their request type is active
- macOS justification required whenever OS = macOS is selected (Step 4), regardless of request type
- Stricter macOS justification enforced when staff category = WPP ET Staff or India HQ

## Setup & Run

```bash
cd Application
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
# Open http://localhost:8900
```
