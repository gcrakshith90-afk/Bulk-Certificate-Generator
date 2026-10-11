from models import ActivityLog
from extensions import db


def test_activity_logging_and_filtering(admin_client, app):
    with app.app_context():
        log1 = ActivityLog(event_type="JOB_CREATED", description="Job #1 created")
        log2 = ActivityLog(event_type="CSV_UPLOADED", description="CSV uploaded")
        db.session.add_all([log1, log2])
        db.session.commit()

    res = admin_client.get("/activity-logs")
    assert res.status_code == 200
    assert b"JOB_CREATED" in res.data
    assert b"CSV_UPLOADED" in res.data

    res_filtered = admin_client.get("/activity-logs?event_type=JOB_CREATED")
    assert res_filtered.status_code == 200
    assert b"Job #1 created" in res_filtered.data
