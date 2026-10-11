from datetime import datetime, timedelta, timezone, date
from typing import Dict, Any, List
from extensions import db
from models.certificate import Certificate
from models.generation_job import GenerationJob
from models.organization import Organization
from models.activity_log import ActivityLog


def get_dashboard_statistics(start_date: date | None = None, end_date: date | None = None) -> Dict[str, Any]:
    """Calculate dynamic dashboard statistics directly from the database."""
    # Base queries
    cert_query = db.session.query(Certificate)
    job_query = db.session.query(GenerationJob)

    if start_date:
        dt_start = datetime.combine(start_date, datetime.min.time())
        cert_query = cert_query.filter(Certificate.created_at >= dt_start)
        job_query = job_query.filter(GenerationJob.created_at >= dt_start)

    if end_date:
        dt_end = datetime.combine(end_date, datetime.max.time())
        cert_query = cert_query.filter(Certificate.created_at <= dt_end)
        job_query = job_query.filter(GenerationJob.created_at <= dt_end)

    total_certs = cert_query.count()
    successful_certs = cert_query.filter(Certificate.status == "Completed").count()
    failed_certs = cert_query.filter(Certificate.status == "Failed").count()
    pending_certs = cert_query.filter(Certificate.status.in_(["Pending", "Processing"])).count()

    total_jobs = job_query.count()
    processing_jobs = job_query.filter(GenerationJob.status.in_(["Queued", "Processing"])).count()
    total_orgs = Organization.query.count()

    overall_success_rate = 0.0
    if total_certs > 0:
        overall_success_rate = round((successful_certs / total_certs) * 100.0, 1)

    return {
        "total_certificates": total_certs,
        "successful_certificates": successful_certs,
        "failed_certificates": failed_certs,
        "pending_certificates": pending_certs,
        "total_jobs": total_jobs,
        "processing_jobs": processing_jobs,
        "total_organizations": total_orgs,
        "overall_success_rate": overall_success_rate,
    }


def get_dashboard_charts_data(days: int = 7) -> Dict[str, Any]:
    """Generate time-series and breakdown datasets for Chart.js."""
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)

    # 1. Certificates generated per day
    day_labels = []
    day_counts = []
    for d in range(days):
        current_day = start_day + timedelta(days=d)
        day_labels.append(current_day.strftime("%b %d"))
        c_count = (
            Certificate.query.filter(
                Certificate.status == "Completed",
                db.func.date(Certificate.generated_at) == current_day.isoformat(),
            ).count()
        )
        day_counts.append(c_count)

    # 2. Successful vs Failed certificates
    success_count = Certificate.query.filter_by(status="Completed").count()
    failed_count = Certificate.query.filter_by(status="Failed").count()
    pending_count = Certificate.query.filter(Certificate.status.in_(["Pending", "Processing"])).count()

    # 3. Jobs grouped by status
    statuses = ["Queued", "Processing", "Completed", "Completed with failures", "Failed", "Cancelled"]
    jobs_by_status = {}
    for st in statuses:
        jobs_by_status[st] = GenerationJob.query.filter_by(status=st).count()

    # 4. Volume by Organization
    org_volumes = (
        db.session.query(Organization.name, db.func.count(Certificate.id))
        .join(GenerationJob, GenerationJob.organization_id == Organization.id)
        .join(Certificate, Certificate.job_id == GenerationJob.id)
        .group_by(Organization.name)
        .order_by(db.func.count(Certificate.id).desc())
        .limit(6)
        .all()
    )
    org_labels = [ov[0] for ov in org_volumes]
    org_data = [ov[1] for ov in org_volumes]

    return {
        "certs_per_day": {
            "labels": day_labels,
            "data": day_counts,
        },
        "success_vs_fail": {
            "labels": ["Successful", "Failed", "Pending"],
            "data": [success_count, failed_count, pending_count],
        },
        "jobs_by_status": {
            "labels": list(jobs_by_status.keys()),
            "data": list(jobs_by_status.values()),
        },
        "volume_by_org": {
            "labels": org_labels,
            "data": org_data,
        },
    }
