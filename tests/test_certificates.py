import os
from datetime import date
from models import Organization, GenerationJob, Certificate
from extensions import db
from services.certificate_service import OUTPUT_DIR


def test_search_and_filter_certificates(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        job = GenerationJob(
            organization_id=org.id,
            course_name="Machine Learning",
            certificate_title="Certificate of ML",
            issue_date=date.today(),
            total=2,
            completed=2,
            status="Completed",
        )
        db.session.add(job)
        db.session.flush()

        c1 = Certificate(
            job_id=job.id,
            recipient_name="Sam Altman",
            recipient_email="sam@openai.com",
            certificate_code="SEARCH-ML-001",
            status="Completed",
            file_path="mock1.pdf",
        )
        c2 = Certificate(
            job_id=job.id,
            recipient_name="Demis Hassabis",
            recipient_email="demis@deepmind.com",
            certificate_code="SEARCH-ML-002",
            status="Completed",
            file_path="mock2.pdf",
        )
        db.session.add_all([c1, c2])
        db.session.commit()

    # Search for Sam
    res = admin_client.get("/certificates?search=Altman")
    assert res.status_code == 200
    assert b"Sam Altman" in res.data
    assert b"Demis Hassabis" not in res.data


def test_download_completed_certificate(admin_client, app):
    mock_filename = "test_downloadable.pdf"
    file_path = OUTPUT_DIR / mock_filename
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4 Mock PDF Content")

    with app.app_context():
        org = Organization.query.first()
        job = GenerationJob(
            organization_id=org.id,
            course_name="Test Course",
            certificate_title="Test Cert",
            issue_date=date.today(),
            total=1,
            completed=1,
        )
        db.session.add(job)
        db.session.flush()

        cert = Certificate(
            job_id=job.id,
            recipient_name="Download Recipient",
            recipient_email="download@test.com",
            certificate_code="DL-001",
            status="Completed",
            file_path=mock_filename,
        )
        db.session.add(cert)
        db.session.commit()
        cert_id = cert.id

    res = admin_client.get(f"/certificates/{cert_id}/download")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert b"%PDF-1.4 Mock PDF Content" in res.data
    res.close()

    try:
        file_path.unlink(missing_ok=True)
    except Exception:
        pass


def test_prevent_download_of_failed_or_pending_certificate(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        job = GenerationJob(
            organization_id=org.id,
            course_name="Test Course",
            certificate_title="Test Cert",
            issue_date=date.today(),
            total=1,
        )
        db.session.add(job)
        db.session.flush()

        cert = Certificate(
            job_id=job.id,
            recipient_name="Pending Recipient",
            recipient_email="pending@test.com",
            certificate_code="PENDING-001",
            status="Pending",
            file_path=None,
        )
        db.session.add(cert)
        db.session.commit()
        cert_id = cert.id

    res = admin_client.get(f"/certificates/{cert_id}/download", follow_redirects=True)
    assert res.status_code == 200
    assert b"cannot be downloaded" in res.data


def test_unauthorized_download_redirects(client, app):
    # Anonymous client attempting download
    res = client.get("/certificates/1/download")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
