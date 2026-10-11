from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort, jsonify
from extensions import db
from models.generation_job import GenerationJob
from models.certificate import Certificate
from models.organization import Organization
from models.activity_log import ActivityLog
from routes.auth_routes import login_required, get_current_user
from tasks.certificate_tasks import enqueue_retry_job
from services.zip_service import create_job_certificates_zip

job_bp = Blueprint("jobs", __name__, url_prefix="/jobs")


@job_bp.route("", methods=["GET"])
@login_required
def list_jobs():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    org_filter = request.args.get("org_id", type=int)
    source_filter = request.args.get("source", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = GenerationJob.query.join(Organization, GenerationJob.organization_id == Organization.id)

    if search:
        # Match Job ID or Organization name or course name
        if search.isdigit():
            query = query.filter(
                db.or_(
                    GenerationJob.id == int(search),
                    Organization.name.ilike(f"%{search}%"),
                    GenerationJob.course_name.ilike(f"%{search}%"),
                )
            )
        else:
            query = query.filter(
                db.or_(
                    Organization.name.ilike(f"%{search}%"),
                    GenerationJob.course_name.ilike(f"%{search}%"),
                    GenerationJob.certificate_title.ilike(f"%{search}%"),
                )
            )

    if status_filter:
        query = query.filter(GenerationJob.status == status_filter)

    if org_filter:
        query = query.filter(GenerationJob.organization_id == org_filter)

    if source_filter:
        query = query.filter(GenerationJob.source_type == source_filter)

    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(GenerationJob.created_at >= df)
        except Exception:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(GenerationJob.created_at <= dt.replace(hour=23, minute=59, second=59))
        except Exception:
            pass

    pagination = query.order_by(GenerationJob.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    organizations = Organization.query.order_by(Organization.name.asc()).all()

    return render_template(
        "jobs.html",
        jobs=pagination.items,
        pagination=pagination,
        organizations=organizations,
        search=search,
        status_filter=status_filter,
        org_filter=org_filter,
        source_filter=source_filter,
        date_from=date_from,
        date_to=date_to,
    )


@job_bp.route("/<int:job_id>", methods=["GET"])
@login_required
def view_job(job_id: int):
    job = db.session.get(GenerationJob, job_id)
    if not job:
        abort(404, description=f"Generation Job #{job_id} not found.")

    cert_status = request.args.get("cert_status", "").strip()
    cert_search = request.args.get("cert_search", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    cert_query = Certificate.query.filter(Certificate.job_id == job.id)

    if cert_status:
        cert_query = cert_query.filter(Certificate.status == cert_status)

    if cert_search:
        cert_query = cert_query.filter(
            db.or_(
                Certificate.recipient_name.ilike(f"%{cert_search}%"),
                Certificate.recipient_email.ilike(f"%{cert_search}%"),
                Certificate.certificate_code.ilike(f"%{cert_search}%"),
            )
        )

    certs_pagination = cert_query.order_by(Certificate.id.asc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "job_details.html",
        job=job,
        certificates=certs_pagination.items,
        pagination=certs_pagination,
        cert_status=cert_status,
        cert_search=cert_search,
    )


@job_bp.route("/<int:job_id>/progress", methods=["GET"])
@login_required
def get_job_progress(job_id: int):
    """Real-time progress polling endpoint for front-end progress updates."""
    job = db.session.get(GenerationJob, job_id)
    if not job:
        return jsonify({"success": False, "error": "Job not found"}), 404

    return jsonify({
        "success": True,
        "id": job.id,
        "status": job.status,
        "total": job.total,
        "completed": job.completed,
        "failed": job.failed,
        "pending": job.pending_count,
        "progress_percentage": job.progress_percentage,
        "success_rate": job.success_rate,
        "is_finished": job.status in ["Completed", "Completed with failures", "Failed", "Cancelled"],
    })


@job_bp.route("/<int:job_id>/retry", methods=["POST"])
@login_required
def retry_job(job_id: int):
    job = db.session.get(GenerationJob, job_id)
    if not job:
        abort(404, description=f"Job #{job_id} not found.")

    failed_count = Certificate.query.filter_by(job_id=job.id, status="Failed").count()
    if failed_count == 0:
        flash("No failed certificates to retry for this job.", "info")
        return redirect(url_for("jobs.view_job", job_id=job.id))

    enqueue_retry_job(job.id)
    flash(f"Retry initiated for {failed_count} failed certificates. Progress will update in the background.", "success")
    return redirect(url_for("jobs.view_job", job_id=job.id))


@job_bp.route("/<int:job_id>/cancel", methods=["POST"])
@login_required
def cancel_job(job_id: int):
    job = db.session.get(GenerationJob, job_id)
    if not job:
        abort(404, description=f"Job #{job_id} not found.")

    if job.status in ["Queued", "Processing"]:
        user = get_current_user()
        job.status = "Cancelled"
        job.completed_at = datetime.now(timezone.utc)

        log = ActivityLog(
            user_id=user.id if user else None,
            job_id=job.id,
            event_type="JOB_CANCELLED",
            description=f"Job #{job.id} was cancelled by {user.name if user else 'User'}.",
        )
        db.session.add(log)
        db.session.commit()
        flash(f"Job #{job.id} has been cancelled.", "warning")
    else:
        flash(f"Job #{job.id} is already in state '{job.status}' and cannot be cancelled.", "info")

    return redirect(url_for("jobs.view_job", job_id=job.id))


@job_bp.route("/<int:job_id>/download-zip", methods=["GET"])
@login_required
def download_zip(job_id: int):
    user = get_current_user()
    zip_path, err, count = create_job_certificates_zip(job_id)
    if err or not zip_path:
        flash(err or "Unable to prepare ZIP archive.", "danger")
        return redirect(url_for("jobs.view_job", job_id=job_id))

    # Log download activity
    log = ActivityLog(
        user_id=user.id if user else None,
        job_id=job_id,
        event_type="ZIP_DOWNLOADED",
        description=f"Downloaded ZIP archive for Job #{job_id} containing {count} certificates.",
    )
    db.session.add(log)
    db.session.commit()

    return send_file(
        str(zip_path),
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_path.name,
    )
