# University IAM Project

Identity and Access Management project for a university context.

This repository currently focuses on Project 1 (Identity Management) and includes the initial foundation needed for Project 2 (Authentication and Authorization).

## 1. What This Project Contains

- Flask application with app factory pattern
- SQLAlchemy models for university identities
- UI routes and templates for identity management
- API blueprint structure for identity, authentication, and admin APIs
- Database reset and fresh start scripts for fast local iteration
- Environment-based configuration

Main folders:

- app/models: identity domain models (User, Student, Faculty, Staff, External, history, sequence)
- app/routes: UI routes for web pages
- app/api: API route skeletons
- app/templates: HTML templates for list, detail, forms, dashboards
- app/services: business logic and validation services
- scripts: helper scripts for reset and startup

## 2. What Is Implemented Until Now

### Project 1: Identity Management

Implemented:

- Common identity data for all individuals:
  - first name, last name
  - date of birth, place of birth
  - nationality, gender
  - personal email, phone
- Category-specific models and fields:
  - Student
  - Faculty
  - Staff
  - External
- Identifier generation with format:
  - STUYYYYNNNNN, FACYYYYNNNNN, STFYYYYNNNNN
  - PHDYYYYNNNNN for PhD students
  - TMPYYYYNNNNN for temporary staff
  - EXTYYYYNNNNN for external identities
- Lifecycle statuses and transition validation:
  - pending, active, suspended, inactive, archived
- Identity CRUD flow in UI:
  - create, list, search, view, edit, deactivate
- Search filters:
  - free text, type, status, year
- Duplicate and data validation rules:
  - duplicate identity check (name + date of birth)
  - unique email
  - numeric phone
  - date validation
  - minimum age for student
- Modification history tracking:
  - create/update/status change logs

### Setup utilities

Implemented:

- scripts/reset_db.py:
  - creates database when needed (MySQL)
  - drops all tables
  - recreates all tables
- scripts/start_fresh.sh:
  - runs reset
  - starts the Flask app

## 3. Quick Start (Step by Step)

### Prerequisites

- Python 3.10+
- MySQL running locally or remotely
- Correct database credentials in .env

### Setup and run

1. Move to project root

    cd /home/argaz/IAM_Project

2. Create virtual environment (first time)

    python3 -m venv .venv

3. Activate virtual environment

    source .venv/bin/activate

4. Install dependencies

    pip install -r requirements.txt

5. Review environment config in .env

Required values:

- FLASK_ENV=development
- DB_HOST
- DB_PORT
- DB_NAME
- DB_USER
- DB_PASSWORD

6. Make startup script executable (first time)

    chmod +x scripts/start_fresh.sh

7. Reset database and start app

    ./scripts/start_fresh.sh

8. Open in browser

- http://127.0.0.1:5000

## 4. Useful Commands

Only reset database:

    .venv/bin/python scripts/reset_db.py --env development

Start app without reset:

    .venv/bin/python run.py

Use a different Python interpreter with start script:

    PYTHON_BIN=/home/argaz/CTF/venv/bin/python ./scripts/start_fresh.sh

## 5. Swagger API Usage

Open Swagger UI:

- http://127.0.0.1:5000/api/doc

Identity endpoints:

- GET /api/identity/examples (ready payloads for student, faculty, staff, external)
- POST /api/identity/
- GET /api/identity/
- GET /api/identity/{id}
- PUT /api/identity/{id}
- DELETE /api/identity/{id}
- GET /api/identity/search

Admin authentication endpoints:

- POST /api/auth/admin/register
- POST /api/auth/login

Notes:

- If ADMIN_BOOTSTRAP_KEY is set in environment, include bootstrap_key in register payload.
- Web login page uses same admin credentials at /auth/login.

## 6. What Still Needs to Be Implemented

### Project 2: Authentication

To implement next:

- Login and logout flow
- Password policy enforcement
  - complexity and length
  - password history
  - lockout after failed attempts
- First login forced password change
- Password reset flow by token
- Session management and remember me
- Login history and authentication events

### Multi-Factor Authentication (MFA)

To implement next:

- OTP via email or SMS
- TOTP via authenticator app
- Security questions
- Authentication levels L1 to L4
- Role-based required level rules

### Authorization

To implement next:

- Role model and permission model
- Route protection decorators
- Admin-only endpoints and views
- Permission checks for operations

### Security and Audit

To implement next:

- Full audit table for authentication events
- IP, session id, success/failure, reason
- suspicious activity alerts

### API completion

To implement next:

- Replace API placeholders with real services
- input schema validation
- consistent error responses

## 7. Recommended Next Order

1. Implement authentication core (password login + lockout + reset)
2. Implement MFA methods and user level enforcement
3. Implement authorization roles and route guards
4. Complete admin security dashboard and audit views
5. Add tests for identity + auth + authorization

## 8. Important Notes

- scripts/reset_db.py is destructive and removes all existing data.
- Use a separate database for development and testing.
- Keep .env secrets out of version control.
