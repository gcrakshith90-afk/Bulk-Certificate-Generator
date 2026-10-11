import threading
import queue
import time
from datetime import datetime, timezone
from typing import Optional

# Global task queue and active tracking
_task_queue = queue.Queue()
_active_jobs = set()
_lock = threading.Lock()
_worker_started = False


def enqueue_generation_job(job_id: int):
    """Safely enqueue a generation job to the background worker."""
    with _lock:
        if job_id not in _active_jobs:
            _active_jobs.add(job_id)
            _task_queue.put(("GENERATE", job_id))


def enqueue_retry_job(job_id: int):
    """Safely enqueue retrying failed certificates for a job."""
    with _lock:
        if job_id not in _active_jobs:
            _active_jobs.add(job_id)
            _task_queue.put(("RETRY", job_id))


def background_worker_loop(app):
    """Background worker loop processing queued certificate jobs."""
    while True:
        try:
            task_type, job_id = _task_queue.get()
            with app.app_context():
                if task_type == "GENERATE":
                    process_job_generation(job_id)
                elif task_type == "RETRY":
                    process_job_retry(job_id)
            _task_queue.task_done()
        except Exception as e:
            time.sleep(1)
        finally:
            with _lock:
                _active_jobs.discard(job_id)


def start_background_worker(app):
    """Initialize and start background worker thread if not already running."""
    global _worker_started
    with _lock:
        if not _worker_started:
            worker_thread = threading.Thread(
                target=background_worker_loop,
                args=(app,),
                daemon=True,
                name="CertiFlow-Background-Worker",
            )
            worker_thread.start()
            _worker_started = True


def process_job_generation(job_id: int):
    """Process all pending certificates for a generation job."""
    from extensions import db
    from models.generation_job import GenerationJob
    from models.certificate import Certificate
    from models.activity_log import ActivityLog
    from services.certificate_service import generate_certificate_pdf

    job = db.session.get(GenerationJob, job_id)
    if not job:
        return

    if job.status == "Cancelled":
        return

    # Update job to Processing
    job.status = "Processing"
    if not job.started_at:
        job.started_at = datetime.now(timezone.utc)
    db.session.commit()

    log_start = ActivityLog(
        job_id=job.id,
        event_type="GENERATION_STARTED",
        description=f"Background generation started for Job #{job.id} ({job.total} recipients).",
    )
    db.session.add(log_start)
    db.session.commit()

    # Query pending certificates
    pending_certs = Certificate.query.filter(
        Certificate.job_id == job.id,
        Certificate.status.in_(["Pending", "Processing"]),
    ).all()

    for cert in pending_certs:
        # Check if job was cancelled during processing
        db.session.refresh(job)
        if job.status == "Cancelled":
            break

        cert.status = "Processing"
        db.session.commit()

        # Generate PDF outside transaction
        success, error_msg, filename = generate_certificate_pdf(
            certificate_code=cert.certificate_code,
            organization_name=job.organization.name if job.organization else "Organization",
            certificate_title=job.certificate_title,
            recipient_name=cert.recipient_name,
            recipient_email=cert.recipient_email,
            course_name=job.course_name,
            issue_date=job.issue_date,
            completion_date=job.completion_date,
            signatory_name=job.signatory_name,
            signatory_designation=job.signatory_designation,
        )

        db.session.refresh(job)
        if success and filename:
            cert.status = "Completed"
            cert.file_path = filename
            cert.error_message = None
            cert.generated_at = datetime.now(timezone.utc)
            job.completed += 1
            
            act = ActivityLog(
                job_id=job.id,
                certificate_id=cert.id,
                event_type="CERTIFICATE_GENERATED",
                description=f"Certificate {cert.certificate_code} generated for {cert.recipient_name}.",
            )
            db.session.add(act)
        else:
            cert.status = "Failed"
            cert.file_path = None
            cert.error_message = error_msg or "Unknown generation error"
            job.failed += 1
            
            act = ActivityLog(
                job_id=job.id,
                certificate_id=cert.id,
                event_type="CERTIFICATE_FAILED",
                description=f"Generation failed for {cert.recipient_name}: {cert.error_message}",
            )
            db.session.add(act)

        job.update_status_from_counters()
        db.session.commit()

    # Finalize job status
    db.session.refresh(job)
    if job.status != "Cancelled":
        job.update_status_from_counters()
        if not job.completed_at:
            job.completed_at = datetime.now(timezone.utc)

        final_event = "JOB_COMPLETED" if job.failed == 0 else "JOB_COMPLETED_WITH_FAILURES"
        log_end = ActivityLog(
            job_id=job.id,
            event_type=final_event,
            description=f"Job #{job.id} finished with status '{job.status}'. Completed: {job.completed}, Failed: {job.failed}.",
        )
        db.session.add(log_end)
        db.session.commit()


def process_job_retry(job_id: int):
    """Retry all failed certificates for a generation job."""
    from extensions import db
    from models.generation_job import GenerationJob
    from models.certificate import Certificate
    from models.activity_log import ActivityLog
    from services.certificate_service import generate_certificate_pdf

    job = db.session.get(GenerationJob, job_id)
    if not job:
        return

    failed_certs = Certificate.query.filter_by(job_id=job.id, status="Failed").all()
    if not failed_certs:
        return

    # Decrement failed counter and reset cert status
    job.failed = max(0, job.failed - len(failed_certs))
    job.status = "Processing"
    for c in failed_certs:
        c.status = "Pending"
        c.error_message = None
    db.session.commit()

    log_retry = ActivityLog(
        job_id=job.id,
        event_type="CERTIFICATE_RETRIED",
        description=f"Initiated retry for {len(failed_certs)} failed certificates in Job #{job.id}.",
    )
    db.session.add(log_retry)
    db.session.commit()

    # Process pending certificates
    process_job_generation(job_id)
