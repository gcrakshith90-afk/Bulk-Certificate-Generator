from datetime import date
from models import Organization, GenerationJob, Certificate
from extensions import db


def test_api_list_jobs(client, app):
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_api_create_job_json(client, app):
    with app.app_context():
        org = Organization.query.first()
        org_id = org.id

    payload = {
        "organization_id": org_id,
        "course_name": "API Automation Mastery",
        "certificate_title": "Certificate of Completion",
        "issue_date": "2026-10-11",
        "recipients": [
            {"name": "API Recipient 1", "email": "api1@test.com"},
            {"name": "API Recipient 2", "email": "api2@test.com"},
        ],
    }

    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["course_name"] == "API Automation Mastery"
    assert data["data"]["total"] == 2


def test_api_create_job_missing_fields_returns_400(client, app):
    payload = {
        "course_name": "",  # missing course name and issue date
    }
    res = client.post("/api/v1/jobs", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False


def test_api_get_nonexistent_job_returns_404(client, app):
    res = client.get("/api/v1/jobs/99999")
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False


def test_api_get_nonexistent_certificate_returns_404(client, app):
    res = client.get("/api/v1/certificates/99999")
    assert res.status_code == 404
    data = res.get_json()
    assert data["success"] is False


def test_api_dashboard_stats(client, app):
    res = client.get("/api/v1/dashboard/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "total_certificates" in data["data"]
    assert "overall_success_rate" in data["data"]
