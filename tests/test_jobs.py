from datetime import date
from models import Organization, GenerationJob, Certificate
from tasks.certificate_tasks import process_job_retry
from extensions import db


def test_job_progress_and_success_rate_calculations(app):
    with app.app_context():
        # Empty job test: division by zero handled safely
        empty_job = GenerationJob(
            organization_id=1,
            course_name="Empty",
            certificate_title="Title",
            issue_date=date.today(),
            total=0,
            completed=0,
            failed=0,
        )
        assert empty_job.progress_percentage == 0.0
        assert empty_job.success_rate == 0.0

        # Normal job
        job = GenerationJob(
            organization_id=1,
            course_name="DevOps",
            certificate_title="Title",
            issue_date=date.today(),
            total=10,
            completed=7,
            failed=1,
        )
        # progress = (7 + 1) / 10 * 100 = 80.0
        assert job.progress_percentage == 80.0
        # success = 7 / 10 * 100 = 70.0
        assert job.success_rate == 70.0
        assert job.pending_count == 2


def test_retry_failed_certificates(app, monkeypatch):
    with app.app_context():
        org = Organization.query.first()
        job = GenerationJob(
            organization_id=org.id,
            course_name="Retry Test Course",
            certificate_title="Cert",
            issue_date=date.today(),
            total=2,
            completed=1,
            failed=1,
            status="Completed with failures",
        )
        db.session.add(job)
        db.session.flush()

        c_pass = Certificate(
            job_id=job.id,
            recipient_name="Already Passed",
            recipient_email="pass@test.com",
            certificate_code="PASS-01",
            status="Completed",
            file_path="cert_pass.pdf",
        )
        c_fail = Certificate(
            job_id=job.id,
            recipient_name="Failed One",
            recipient_email="fail@test.com",
            certificate_code="RETRY-01",
            status="Failed",
            error_message="Previous error",
        )
        db.session.add_all([c_pass, c_fail])
        db.session.commit()
        job_id = job.id

    # Now make generation succeed on retry
    def mock_retry_generate(certificate_code, **kwargs):
        return True, None, f"cert_{certificate_code}.pdf"

    monkeypatch.setattr("services.certificate_service.generate_certificate_pdf", mock_retry_generate)

    with app.app_context():
        process_job_retry(job_id)

        job_updated = db.session.get(GenerationJob, job_id)
        assert job_updated.failed == 0
        assert job_updated.completed == 2
        assert job_updated.status == "Completed"

        c_retried = Certificate.query.filter_by(certificate_code="RETRY-01").first()
        assert c_retried.status == "Completed"
        assert c_retried.error_message is None
