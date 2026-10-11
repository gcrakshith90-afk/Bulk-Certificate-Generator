from datetime import date
from pathlib import Path
from services.certificate_service import generate_certificate_pdf, OUTPUT_DIR
from tasks.certificate_tasks import process_job_generation
from models import Organization, GenerationJob, Certificate
from extensions import db


def test_generate_actual_pdf_integration(app):
    """Integration test verifying actual PDF generation and verification."""
    success, error, filename = generate_certificate_pdf(
        certificate_code="INT-TEST-001",
        organization_name="Apex Test Institute",
        certificate_title="Certificate of Competency",
        recipient_name="John Doe Test",
        recipient_email="john.doe@test.local",
        course_name="Automated Testing in Python",
        issue_date=date.today(),
        signatory_name="Director Test",
    )

    assert success is True
    assert error is None
    assert filename is not None

    pdf_file = OUTPUT_DIR / filename
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 500

    # Verify PDF magic bytes
    with open(pdf_file, "rb") as f:
        header = f.read(5)
        assert header.startswith(b"%PDF")

    # Clean up test file
    pdf_file.unlink(missing_ok=True)


def test_process_job_failure_isolation(app, monkeypatch):
    """Test that a failure in one recipient does not stop other recipients in the job."""
    with app.app_context():
        org = Organization.query.first()
        job = GenerationJob(
            organization_id=org.id,
            course_name="Isolation Test Course",
            certificate_title="Certificate of Isolation",
            issue_date=date.today(),
            total=2,
            completed=0,
            failed=0,
            source_type="manual",
        )
        db.session.add(job)
        db.session.flush()

        cert1 = Certificate(
            job_id=job.id,
            recipient_name="Recipient Fail",
            recipient_email="fail@test.com",
            certificate_code="FAIL-001",
            status="Pending",
        )
        cert2 = Certificate(
            job_id=job.id,
            recipient_name="Recipient Succeed",
            recipient_email="succeed@test.com",
            certificate_code="SUCCEED-002",
            status="Pending",
        )
        db.session.add_all([cert1, cert2])
        db.session.commit()
        job_id = job.id

    # Mock certificate generation so recipient 1 raises an error while recipient 2 succeeds
    from services import certificate_service

    orig_generate = certificate_service.generate_certificate_pdf

    def mock_generate(certificate_code, **kwargs):
        if "FAIL" in certificate_code:
            return False, "Simulated PDF render failure", None
        return orig_generate(certificate_code, **kwargs)

    monkeypatch.setattr("services.certificate_service.generate_certificate_pdf", mock_generate)

    # Process job directly
    with app.app_context():
        process_job_generation(job_id)

        job_result = db.session.get(GenerationJob, job_id)
        assert job_result.completed == 1
        assert job_result.failed == 1
        assert job_result.status == "Completed with failures"

        c1 = Certificate.query.filter_by(certificate_code="FAIL-001").first()
        c2 = Certificate.query.filter_by(certificate_code="SUCCEED-002").first()

        assert c1.status == "Failed"
        assert "Simulated PDF render failure" in c1.error_message
        assert c2.status == "Completed"
        assert c2.file_path is not None
