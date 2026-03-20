# WPP Laptop Request System — Full Application Expansion Design

**Date:** 2026-03-20
**Status:** Approved

## Overview

Expand the existing Flask-based laptop request wizard into a full application with user authentication, MongoDB data storage, and CRUD management. The system supports two roles: super admin (manages users, views all data) and regular user (submits and manages own requests).

## Architecture

```
Browser ──► Flask (server.py)
              ├── /login, /logout          (认证)
              ├── /api/users/*             (用户管理, 管理员)
              ├── /api/applications/*      (申请 CRUD + 导出)
              └── static/
                    ├── index.html         (向导, 改造)
                    ├── login.html         (新增)
                    └── dashboard.html     (新增, 列表+管理)

MongoDB (Docker) ──► Collections:
              ├── users                    (用户信息+认证)
              └── applications             (申请数据)
```

- Flask app runs locally, connects to MongoDB via `localhost:27017`
- MongoDB runs in Docker with volume persistence
- Flask-Login manages sessions; unauthenticated requests redirect to login

## Data Model

### users Collection

```json
{
  "_id": ObjectId,
  "username": "parker.lu",
  "password_hash": "bcrypt...",
  "email": "parker.lu@wpp.com",
  "name": "Parker Lu",
  "opco": "VML",
  "market": "Shanghai",
  "role": "admin | user",
  "must_change_password": false,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### applications Collection

```json
{
  "_id": ObjectId,
  "request_id": "REQ-2026-03-20-001-VML",
  "user_id": ObjectId,
  "status": "submitted",
  "data": { /* 现有向导 collectData() 的完整 JSON */ },
  "created_at": ISODate,
  "updated_at": ISODate
}
```

Key decisions:
- `data` field stores the full wizard JSON as-is, minimizing wizard changes
- `user_id` links to the submitter for permission filtering
- `request_id` retains existing numbering logic (REQ-YYYY-MM-DD-###-OpCo)
- When creating a request, `requestorName`, `email`, `agency` (OpCo), `market` auto-populate from user profile

## API Design

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/login` | Login, returns session |
| POST | `/api/logout` | Logout |
| GET | `/api/me` | Get current user info |
| POST | `/api/change-password` | Change password |

### Application Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/applications` | List (user sees own, admin sees all) |
| POST | `/api/applications` | Create new request |
| GET | `/api/applications/:id` | Get single request |
| PUT | `/api/applications/:id` | Update (own only, admin can update all) |
| DELETE | `/api/applications/:id` | Delete (own only, admin can delete all) |
| GET | `/api/applications/export` | Batch export to Excel |

### User Management (Admin Only)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users` | List users |
| POST | `/api/users` | Create user |
| PUT | `/api/users/:id` | Edit user |
| DELETE | `/api/users/:id` | Delete user |

All APIs require login (401 if not). Admin-only APIs return 403 for non-admins.

## Frontend Pages

### login.html
- Username + password form
- WPP brand styling (#0033A0)
- Force password change modal on first login (`must_change_password: true`)

### dashboard.html
Left sidebar navigation + right content area:

**User view:**
- "My Applications" — table with Request ID, OpCo, device model, date, action buttons
- "New Application" — navigates to wizard
- "Change Password"

**Admin additional views:**
- "All Applications" — full list with filter by user/OpCo/Market
- "User Management" — user CRUD table
- "Batch Export" — filter and export to Excel

**List action buttons:**
- View (read-only review)
- Edit (opens wizard with pre-filled data)
- Delete (with confirmation)

### index.html (Wizard Modifications)
- Requires login to access
- New mode: auto-fills OpCo, Market, Name, Email from user profile
- Edit mode: loads existing application data into form fields, submits via PUT
- After submit, redirects back to dashboard

## Docker & Deployment

### docker-compose.yml

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

- MongoDB without auth (local dev environment)
- Data persisted via Docker volume
- Flask app runs locally (not containerized)

### New Python Dependencies

```
flask-login     # Session management
pymongo         # MongoDB driver
bcrypt          # Password hashing
```

### Initialization Logic

On server startup, check `users` collection:
- If empty, create default admin: username `admin`, password `admin123`, `must_change_password: true`
- Print reminder to console

### start.sh Changes

- Check if Docker MongoDB is running; if not, run `docker compose up -d`
- Then start Flask as before

## Authentication & Authorization

- **Login:** Username + password, bcrypt hash comparison
- **Session:** Flask-Login with server-side sessions
- **Roles:** `admin` and `user`
- **Admin creates all users** — no self-registration
- **Default admin:** `admin / admin123`, must change password on first login

## User Management (Admin)

Admin can create users with fields:
- Username, password, email, name, OpCo, market, role

Admin can edit and delete users.

## Application CRUD

- Users can create, view, edit, and delete their own applications at any time
- Admins can view, edit, and delete all applications
- Create and edit both use the existing wizard form
- Batch export generates a single Excel file with multiple rows

## Migration

- Existing `.md` and `.xlsx` files in `applications/` directory are left as-is (historical records)
- New submissions go to MongoDB only
- No file generation on submit; Excel generated dynamically on export
