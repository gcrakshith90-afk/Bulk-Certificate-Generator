from datetime import date
from models import Organization, GenerationJob, Certificate
from extensions import db


def test_dashboard_statistics(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        job = GenerationJob(
            organization_id=org.id,
            course_name="Dashboard Test",
            certificate_title="Test Cert",
            issue_date=date.today(),
            total=4,
            completed=3,
            failed=1,
            status="Completed with failures",
        )
        db.session.add(job)
        db.session.flush()

        for i in range(3):
            c = Certificate(
                job_id=job.id,
                recipient_name=f"Pass {i}",
                recipient_email=f"pass{i}@test.com",
                certificate_code=f"DASH-P-{i}",
                status="Completed",
                file_path=f"file{i}.pdf",
            )
            db.session.add(c)
        cf = Certificate(
            job_id=job.id,
            recipient_name="Fail 1",
            recipient_email="fail@test.com",
            certificate_code="DASH-F-1",
            status="Failed",
            error_message="Render error",
        )
        db.session.add(cf)
        db.session.commit()

    res = admin_client.get("/dashboard")
    assert res.status_code == 200
    assert b"Dashboard Overview" in res.data
    assert b"75.0%" in res.data  # 3/4 = 75.0% success rate


def test_dashboard_charts_api(client, app):
    res = client.get("/api/v1/dashboard/charts?days=7")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "certs_per_day" in data["data"]
    assert "success_vs_fail" in data["data"]
    assert "jobs_by_status" in data["data"]
    assert "volume_by_org" in data["data"]
