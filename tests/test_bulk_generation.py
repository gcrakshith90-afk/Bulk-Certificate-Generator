import json
from models import Organization, GenerationJob, Certificate
from extensions import db


def test_bulk_generation_manual_success(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        org_id = org.id

    recipients = [
        {"name": "Dev Alice", "email": "alice.dev@example.com"},
        {"name": "Dev Bob", "email": "bob.dev@example.com"},
    ]
    data = {
        "organization_id": org_id,
        "course_name": "Full-Stack Python",
        "certificate_title": "Certificate of Completion",
        "issue_date": "2026-10-11",
        "recipients_json": json.dumps(recipients),
    }

    res = admin_client.post("/bulk-generation/manual", data=data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Full-Stack Python" in res.data

    with app.app_context():
        job = GenerationJob.query.filter_by(course_name="Full-Stack Python").first()
        assert job is not None
        assert job.total == 2
        assert job.certificates.count() == 2


def test_bulk_generation_empty_recipients_fails(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        org_id = org.id

    data = {
        "organization_id": org_id,
        "course_name": "Ghost Course",
        "certificate_title": "Certificate of Completion",
        "issue_date": "2026-10-11",
        "recipients_json": json.dumps([]),
    }
    res = admin_client.post("/bulk-generation/manual", data=data, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please enter at least one recipient" in res.data


def test_bulk_generation_auto_create_new_org(admin_client, app):
    recipients = [{"name": "Charlie New", "email": "charlie@neworg.com"}]
    data = {
        "organization_id": "NEW",
        "new_organization_name": "Brand New Robotics Academy",
        "course_name": "Robotics 101",
        "certificate_title": "Certificate of Achievement",
        "issue_date": "2026-10-11",
        "recipients_json": json.dumps(recipients),
    }

    res = admin_client.post("/bulk-generation/manual", data=data, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        org = Organization.query.filter_by(name="Brand New Robotics Academy").first()
        assert org is not None
        job = GenerationJob.query.filter_by(organization_id=org.id).first()
        assert job is not None
        assert job.total == 1
