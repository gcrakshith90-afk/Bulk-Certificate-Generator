# CertiFlow – Bulk Certificate Management System

**CertiFlow** is an enterprise-grade full-stack web application designed for companies, colleges, universities, and training institutes to generate, manage, verify, and distribute personalized PDF certificates at scale.

Built with **Python**, **Flask**, **Jinja2**, **Bootstrap 5**, and **SQLite / SQLAlchemy**, CertiFlow features an asynchronous background processing engine, dual-generation workflows (interactive manual recipient entry and high-performance CSV batch ingestion), dynamic Chart.js analytics, audit logging, and a versioned REST API.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Technology Stack](#technology-stack)
3. [Architecture and Folder Structure](#architecture-and-folder-structure)
4. [Prerequisites](#prerequisites)
5. [Installation & Virtual Environment Setup](#installation--virtual-environment-setup)
6. [Environment Configuration](#environment-configuration)
7. [Database Initialization & Migrations](#database-initialization--migrations)
8. [Running the Application](#running-the-application)
9. [Default Administrator Account](#default-administrator-account)
10. [Usage Guide](#usage-guide)
    - [Method A: Manual Recipient Entry](#method-a-manual-recipient-entry)
    - [Method B: CSV File Upload & Preview](#method-b-csv-file-upload--preview)
    - [Batch Job Tracking & Retries](#batch-job-tracking--retries)
    - [Certificate Library & Single/Bulk Downloads](#certificate-library--singlebulk-downloads)
11. [REST API Documentation (v1)](#rest-api-documentation-v1)
12. [Background Processing & Concurrency Strategy](#background-processing--concurrency-strategy)
13. [Security Architecture](#security-architecture)
14. [Running Automated Tests](#running-automated-tests)
15. [Production Deployment Guidance](#production-deployment-guidance)

---

## Key Features

- **SaaS-Style Light Dashboard**: Dark navy sidebar (`#0f172a`), clean white content panels, stat cards, and interactive Chart.js visualizations (daily generation volume, status doughnut, volume by organization, jobs breakdown).
- **Dual Ingestion Pipelines**:
  - **Manual Entry**: Dynamically add and remove recipient rows on the fly, client-side email verification, and instant modal preview of the certificate template.
  - **CSV Upload**: Robust parsing handling standard UTF-8 and UTF-8-BOM, CSV formula injection sanitization, detection of malformed records and intra-file duplicate emails, with an interactive preview table before generation is confirmed.
- **Resilient PDF Generation Engine**:
  - A4 Landscape orientation with royal blue and gold decorative double borders, seal emblem, and typography.
  - Primary rendering with **WeasyPrint**; automatic seamless fallback to **ReportLab** if system-level Pango/Cairo GTK3 C-libraries are unavailable on Windows/minimal environments.
  - Per-recipient failure isolation: an individual rendering issue records the specific failure reason without aborting the batch.
- **Job Status Tracking & Retries**:
  - Real-time polling updates progress percentages and state without page reloads.
  - Safe 1-click retry functionality that only re-queues failed recipients while preserving already generated certificates.
  - Job cancellation support between recipient rendering passes.
- **Searchable Certificate Library**:
  - Server-side paginated certificate library with multi-criteria filtering (organization, course name, issue date range, creation date range, status).
  - Search by recipient name, email, or certificate verification code.
  - Individual PDF downloads and bulk ZIP archive export.
- **Organization Management**:
  - Comprehensive management for companies, universities, colleges, and training institutes.
  - Tracks certificate generation volume and job history per organization.
  - Ability to select existing organizations or register new ones inline during certificate generation.
- **Comprehensive Audit Trail**:
  - Real-time event logging (`JOB_CREATED`, `CSV_UPLOADED`, `GENERATION_STARTED`, `CERTIFICATE_GENERATED`, `CERTIFICATE_FAILED`, `CERTIFICATE_RETRIED`, `CERTIFICATE_DOWNLOADED`, `ZIP_DOWNLOADED`).
- **Full REST API (v1)**:
  - Versioned JSON endpoints under `/api/v1/` for programmatic integration with external LMS, ERP, or CRM platforms.

---

## Technology Stack

- **Backend**: Python 3.10+ & Flask 3.x
- **ORM & Database**: Flask-SQLAlchemy, SQLite (production-compatible with PostgreSQL)
- **Database Migrations**: Flask-Migrate (Alembic)
- **Frontend**: HTML5, CSS3, Jinja2 Templates, Bootstrap 5.3, Bootstrap Icons
- **Data Visualizations**: Chart.js 4.4
- **Forms & Validation**: Flask-WTF, WTForms, email-validator
- **PDF Generation**: WeasyPrint with ReportLab fallback engine
- **CSV Processing**: Python standard `csv` library with sanitization
- **Background Worker**: Thread-safe isolated worker queue with atomic database transactions
- **Testing**: pytest

---

## Architecture and Folder Structure

```
Bulk Certificate Generator/
├── app.py                      # Application factory and entry point
├── config.py                   # Configuration classes (Dev, Prod, Test)
├── extensions.py               # Flask extensions (db, migrate, csrf)
├── forms.py                    # WTForms definitions
├── pytest.ini                  # Pytest runner configuration
├── requirements.txt            # Python dependencies
├── sample_recipients.csv       # Ready-to-use sample CSV template
├── .env.example                # Sample environment configuration
├── .gitignore                  # Git ignore rules
│
├── models/                     # SQLAlchemy Models
│   ├── __init__.py
│   ├── user.py                 # User authentication & role model
│   ├── organization.py         # Organization entity & stats
│   ├── generation_job.py       # GenerationJob batch tracking
│   ├── certificate.py          # Certificate entity & unique code generator
│   └── activity_log.py         # Audit logging model
│
├── routes/                     # Blueprint Route Handlers
│   ├── __init__.py
│   ├── auth_routes.py          # Authentication, sessions, & decorators
│   ├── dashboard_routes.py     # Dashboard & system settings
│   ├── organization_routes.py  # Organization CRUD & status toggles
│   ├── bulk_routes.py          # Manual & CSV bulk generation workflows
│   ├── job_routes.py           # Job management, progress, retries & cancel
│   ├── certificate_routes.py   # Certificate library & downloads
│   ├── activity_routes.py      # System audit logs
│   └── api_routes.py           # Versioned REST API (/api/v1)
│
├── services/                   # Business Logic & Core Services
│   ├── __init__.py
│   ├── bulk_service.py         # Atomic job creation & recipient validation
│   ├── csv_service.py          # CSV parsing, validation & sanitization
│   ├── certificate_service.py  # Jinja2 rendering & PDF generator (WeasyPrint / ReportLab)
│   ├── dashboard_service.py    # Metric aggregations & chart data
│   └── zip_service.py          # Secure ZIP bundling & temp file cleanup
│
├── tasks/                      # Background Tasks & Workers
│   ├── __init__.py
│   └── certificate_tasks.py    # Isolated background thread worker & retry logic
│
├── templates/                  # Jinja2 Templates
│   ├── base.html               # Shared layout, navbar & sidebar
│   ├── login.html              # Authentication page
│   ├── dashboard.html          # Analytics dashboard & charts
│   ├── organizations.html      # Organization directory
│   ├── organization_form.html  # Organization add/edit form
│   ├── organization_details.html# Organization profile & jobs
│   ├── bulk_generation.html    # Bulk generator (Manual + CSV tabs)
│   ├── csv_preview.html        # CSV recipient preview & error audit
│   ├── jobs.html               # Job list with filters
│   ├── job_details.html        # Job progress & recipient results
│   ├── certificates.html       # Certificate library table
│   ├── certificate_details.html# Individual certificate record
│   ├── activity_logs.html      # Audit logs list
│   ├── settings.html           # System parameters & guidance
│   └── errors/                 # HTTP Error Pages (400, 403, 404, 500)
│
├── static/                     # Static Assets
│   ├── css/style.css           # SaaS theme CSS
│   └── js/
│       ├── dashboard.js        # Chart.js initialization
│       ├── bulk_generation.js  # Dynamic rows & preview modal
│       └── certificates.js     # Library scripts
│
├── certificate_templates/      # Certificate Jinja2 HTML Templates
│   └── certificate.html        # A4 Landscape royal border template
│
├── tests/                      # Automated pytest Suite
│   ├── conftest.py             # Fixtures & in-memory test databases
│   ├── test_auth.py            # Authentication & authorization tests
│   ├── test_organizations.py   # Organization CRUD & duplicate tests
│   ├── test_bulk_generation.py # Manual generation & validation tests
│   ├── test_csv_upload.py      # CSV validation & injection tests
│   ├── test_certificate_generation.py # Actual PDF generation & failure isolation
│   ├── test_jobs.py            # Progress calculation & retry tests
│   ├── test_certificates.py    # Search, download & permissions tests
│   ├── test_dashboard.py       # Statistics & chart API tests
│   ├── test_activity.py        # Audit trail logging tests
│   └── test_api.py             # REST API endpoint tests
│
├── generated_certificates/     # Generated PDF storage (managed by app)
├── uploads/                    # Staged CSV uploads
├── temp_zips/                  # Temporary ZIP downloads (auto-cleaned)
└── migrations/                 # Alembic database migration scripts
```

---

## Prerequisites

- **Python**: Version 3.10, 3.11, 3.12, or 3.13
- **Pip**: Latest version
- Optional for WeasyPrint on Windows: GTK3 Runtime (If omitted, CertiFlow automatically uses the built-in ReportLab engine to generate certificates seamlessly without any setup).

---

## Installation & Virtual Environment Setup

1. **Clone or navigate to the project directory**:
   ```powershell
   cd "e:\interview_project\Bulk Certificate Generator"
   ```

2. **Create a Python Virtual Environment**:
   ```powershell
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   - **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```

4. **Install Required Packages**:
   ```powershell
   pip install -r requirements.txt
   ```

---

## Environment Configuration

Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Review and adjust variables in `.env`:
```ini
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=0
SECRET_KEY=certiflow-secure-secret-key-change-in-production-2026
DATABASE_URL=sqlite:///certiflow.db

# File and Generation Configuration
MAX_CONTENT_LENGTH=10485760   # 10MB upload limit
MAX_RECIPIENTS_PER_JOB=1000   # Configurable recipient limit per job
UPLOAD_FOLDER=uploads
GENERATED_CERTIFICATES_FOLDER=generated_certificates
TEMP_ZIPS_FOLDER=temp_zips

# Initial Administrator Seed
ADMIN_NAME=CertiFlow Admin
ADMIN_EMAIL=admin@certiflow.local
ADMIN_PASSWORD=Admin@123456
```

---

## Database Initialization & Migrations

CertiFlow automatically verifies and creates the database schema on first launch. If you wish to manage migrations using Flask-Migrate:

```powershell
.\venv\Scripts\flask.exe db migrate -m "Schema update"
.\venv\Scripts\flask.exe db upgrade
```

---

## Running the Application

To launch the CertiFlow server:

```powershell
.\venv\Scripts\python.exe app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## User Registration & Authentication

Users can directly create their own credentials and log in:

1. **Self-Service Registration (`/register`)**:
   - Navigate to `/register` or click **"Create New Account"** on the sign-in page.
   - Enter your **Full Name**, **Email Address**, and **Password** (min 6 characters).
   - Upon registration, you are immediately logged in to your personal dashboard and ready to generate certificates and manage organizations.

2. **Pre-configured Test Account (Optional)**:
   - **Email**: `admin@certiflow.local`
   - **Password**: `Admin@123456`

Two sample organizations (*Stanford Engineering Academy* and *TechPulse Global Institute*) are pre-seeded in the database so you can test bulk generation right away.

---

## Usage Guide

### Method A: Manual Recipient Entry
1. Navigate to **Bulk Generation** (`/bulk-generation`).
2. Select an existing organization or click `+ Register New Organization`.
3. Provide Course / Event Name, Certificate Title, Issue Date, and optional Signatory details.
4. Click **Add Recipient Row** to add as many recipients as needed.
5. Click **Preview Template** to view a live render of the certificate before dispatching.
6. Click **Launch Generation Job**. You will be redirected to the Job Details page where the progress bar advances in real time.

### Method B: CSV File Upload & Preview
1. On the **Bulk Generation** page, select the **Method B: CSV File Upload & Preview** tab.
2. Select or enter the organization, course name, and certificate title.
3. Choose your `.csv` file (or click **Download Sample CSV** to view the format).
4. The CSV must have headers `name` and `email`:
   ```csv
   name,email
   Rakshith,rakshith@example.com
   Priya,priya@example.com
   Arun,arun@example.com
   ```
5. Click **Upload & Preview CSV**.
6. The validation screen audits each row:
   - Green rows indicate valid recipients.
   - Red rows indicate invalid entries (missing fields, invalid email format, or duplicate addresses).
7. Click **Confirm & Generate Certificates**. Only verified recipient records are queued.

### Batch Job Tracking & Retries
- Visit **Generation Jobs** (`/jobs`) to view all batches with status indicators (`Queued`, `Processing`, `Completed`, `Completed with failures`, `Failed`, `Cancelled`).
- Open any job (`/jobs/<job_id>`) to view real-time recipient progress.
- If any recipient encounters an error (e.g. invalid rendering parameter), an individual failure reason is displayed.
- Click **Retry Failed** to retry only the failed recipients without re-generating successful ones.
- Click **Cancel Job** to stop execution between recipient batches.

### Certificate Library & Single/Bulk Downloads
- Visit **Certificates** (`/certificates`) to search across thousands of records by recipient name, email, or verification code.
- Filter by issuing organization, course, generation status, or date ranges.
- Click the download icon on any completed record to download the individual PDF.
- On any job page (`/jobs/<job_id>`), click **Download ZIP** to export all successful certificates in a single ZIP file.

---

## REST API Documentation (v1)

All endpoints are versioned under `/api/v1/` and return consistent JSON structures.

### 1. Dashboard Statistics
- **`GET /api/v1/dashboard/stats`**
  - Query parameters (optional): `start_date=YYYY-MM-DD`, `end_date=YYYY-MM-DD`
  - Response:
    ```json
    {
      "success": true,
      "data": {
        "total_certificates": 150,
        "successful_certificates": 148,
        "failed_certificates": 2,
        "pending_certificates": 0,
        "total_jobs": 5,
        "processing_jobs": 0,
        "total_organizations": 3,
        "overall_success_rate": 98.7
      }
    }
    ```

### 2. Dashboard Charts
- **`GET /api/v1/dashboard/charts?days=7`**
  - Returns time-series daily volume, status distribution, and volume by organization.

### 3. List Jobs
- **`GET /api/v1/jobs?page=1&per_page=10&status=Completed`**
  - Returns paginated list of generation jobs.

### 4. Get Job Details & Recipient Results
- **`GET /api/v1/jobs/<job_id>`**
  - Returns job metadata, counters, progress percentage, and recipient-level records.

### 5. Create Bulk Job (JSON)
- **`POST /api/v1/jobs`**
  - Payload:
    ```json
    {
      "organization_id": 1,
      "course_name": "Cloud Native Architecture",
      "certificate_title": "Certificate of Completion",
      "issue_date": "2026-10-15",
      "signatory_name": "Dr. Sarah Connor",
      "signatory_designation": "Director",
      "recipients": [
        {"name": "Alice Smith", "email": "alice@example.com"},
        {"name": "Bob Jones", "email": "bob@example.com"}
      ]
    }
    ```

### 6. Create Bulk Job (CSV Upload)
- **`POST /api/v1/jobs/csv`**
  - `multipart/form-data`: `csv_file`, `organization_id`, `course_name`, `certificate_title`, `issue_date`.

### 7. Retry Failed Job
- **`POST /api/v1/jobs/<job_id>/retry`**
  - Enqueues retry for all failed recipients in the specified job.

### 8. Download Job ZIP
- **`GET /api/v1/jobs/<job_id>/download-zip`**
  - Streams ZIP archive containing all successful certificate PDFs.

### 9. List Certificates
- **`GET /api/v1/certificates?page=1&per_page=20&search=Smith&status=Completed`**

### 10. Download Single Certificate PDF
- **`GET /api/v1/certificates/<cert_id>/download`**

### 11. Activity Logs
- **`GET /api/v1/activity?page=1&per_page=20&event_type=JOB_CREATED`**

---

## Background Processing & Concurrency Strategy

1. **Isolated Worker Lifecycle**:
   - Background tasks run inside an isolated Python daemon thread consuming from a thread-safe `queue.Queue`.
   - Active jobs are guarded by a thread lock to prevent duplicate concurrent queue submissions of the same batch.
2. **Database Session Safety**:
   - The worker executes inside `app.app_context()` with dedicated database session management.
   - Database transactions are committed per recipient to deliver real-time progress updates to the frontend without holding open locks during PDF generation.
3. **Failure Isolation**:
   - Each recipient rendering step is wrapped in individual exception blocks. If one certificate fails, its state is marked as `Failed` with the exact error message recorded, and the worker immediately proceeds to the next recipient.
4. **Cancellation Support**:
   - Between recipient processing loops, the worker verifies whether the job was flagged as `Cancelled` and cleanly stops execution if requested.

---

## Security Architecture

- **Authentication & Roles**: Secure password hashing with `werkzeug.security` (scrypt / pbkdf2). Role-based authorization distinguishing `Admin` and `Operator` capabilities.
- **CSRF Protection**: All browser forms are protected via `Flask-WTF` CSRF tokens. REST API endpoints under `/api/v1` are explicitly scoped.
- **CSV Formula Injection Mitigation**: Any CSV cell value starting with spreadsheet execution triggers (`=`, `+`, `-`, `@`) is safely neutralized.
- **Path Traversal Prevention**: File downloads strictly sanitize and resolve paths within designated output directories, discarding parent directory navigation (`..`).
- **File Storage Isolation**: Generated certificates and staged uploads reside in dedicated directories outside publicly accessible static folders. Direct file URLs are never exposed.
- **Input Sanitization**: User-supplied values are escaped in Jinja2 templates to prevent Cross-Site Scripting (XSS).

---

## Running Automated Tests

CertiFlow includes a complete automated test suite using **pytest** that validates:
- Application initialization
- Authentication, invalid passwords, account deactivation, and access control
- Organization creation, duplicate name prevention, and status toggles
- Manual bulk generation, empty recipient validation, and auto-created organizations
- CSV parsing, UTF-8-BOM handling, formula injection, and duplicate detection
- Real PDF generation on disk and PDF magic-byte verification
- Per-recipient failure isolation
- Job progress calculations and division-by-zero protection
- Failed certificate retries and counter consistency
- Certificate search, multi-field filtering, and download authorization
- Dashboard metrics and Chart.js API datasets
- Audit trail logging
- Versioned REST API endpoints, status codes, and 404 handlers

Run the entire test suite:
```powershell
.\venv\Scripts\pytest.exe -v
```

Expected output:
```
============================= 39 passed in 12.06s =============================
```

---

## Production Deployment Guidance

### When to Upgrade from SQLite to PostgreSQL
While SQLite is ideal for local development, evaluations, and small-scale operations (up to 5,000 certificates/day), SQLite enforces a database-level write lock. For production environments with concurrent administrators and high-volume batch generation (10,000+ to 100,000+ certificates/day), transition to **PostgreSQL**:
- Set `DATABASE_URL=postgresql://user:password@localhost:5432/certiflow` in `.env`.
- Install `psycopg2-binary`: `pip install psycopg2-binary`.
- Run migrations: `flask db upgrade`.

### Distributed Tasks with Celery & Redis
For enterprise scaling across multiple physical nodes:
1. Replace the local in-process queue with **Celery**:
   ```powershell
   pip install celery redis
   ```
2. Configure Celery broker:
   ```python
   CELERY_BROKER_URL = "redis://localhost:6379/0"
   CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
   ```
3. Run dedicated Celery workers:
   ```bash
   celery -A tasks.celery_worker worker --loglevel=info --concurrency=4
   ```

### Production WSGI Server
Do not use the Flask development server in production. Run CertiFlow using a WSGI server like **Gunicorn** or **Waitress**:

- **Windows (Waitress)**:
  ```powershell
  pip install waitress
  waitress-serve --port=5000 app:app
  ```
- **Linux (Gunicorn)**:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 0.0.0.0:5000 app:app
  ```

---

## License
Proprietary & Confidential. Built for CertiFlow Bulk Certificate Management.
