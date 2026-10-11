import os
from datetime import datetime, date
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, current_app
from extensions import db, csrf
from models.generation_job import GenerationJob
from models.certificate import Certificate
from models.organization import Organization
from models.activity_log import ActivityLog
from services.csv_service import parse_and_validate_csv
from services.bulk_service import resolve_organization, create_bulk_generation_job
from services.zip_service import create_job_certificates_zip
from services.dashboard_service import get_dashboard_statistics, get_dashboard_charts_data
from tasks.certificate_tasks import enqueue_retry_job

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Disable CSRF for REST API endpoints
csrf.exempt(api_bp)

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated_certificates"


@api_bp.route("/dashboard/stats", methods=["GET"])
def api_dashboard_stats():
    start_str = request.args.get("start_date")
    end_str = request.args.get("end_date")
    start_date = None
    end_date = None
    if start_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except Exception:
            pass
    if end_str:
        try:
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except Exception:
            pass

    stats = get_dashboard_statistics(start_date=start_date, end_date=end_date)
    return jsonify({"success": True, "data": stats})


@api_bp.route("/dashboard/charts", methods=["GET"])
def api_dashboard_charts():
    days = request.args.get("days", 7, type=int)
    charts = get_dashboard_charts_data(days=days)
    return jsonify({"success": True, "data": charts})


@api_bp.route("/jobs", methods=["GET"])
def api_list_jobs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status_filter = request.args.get("status")
    org_id = request.args.get("org_id", type=int)

    query = GenerationJob.query
    if status_filter:
        query = query.filter(GenerationJob.status == status_filter)
    if org_id:
        query = query.filter(GenerationJob.organization_id == org_id)

    pagination = query.order_by(GenerationJob.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "data": [job.to_dict() for job in pagination.items],
    })


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def api_get_job(job_id: int):
    job = db.session.get(GenerationJob, job_id)
    if not job:
        return jsonify({"success": False, "error": f"Job #{job_id} not found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    cert_status = request.args.get("status")

    cert_query = Certificate.query.filter(Certificate.job_id == job.id)
    if cert_status:
        cert_query = cert_query.filter(Certificate.status == cert_status)

    pagination = cert_query.order_by(Certificate.id.asc()).paginate(page=page, per_page=per_page, error_out=False)

    job_data = job.to_dict()
    job_data["recipients"] = [c.to_dict() for c in pagination.items]
    job_data["recipients_pagination"] = {
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    }

    return jsonify({"success": True, "data": job_data})


@api_bp.route("/jobs", methods=["POST"])
def api_create_job():
    payload = request.get_json()
    if not payload:
        return jsonify({"success": False, "error": "JSON payload required"}), 400

    course_name = payload.get("course_name")
    certificate_title = payload.get("certificate_title", "Certificate of Completion")
    issue_date_str = payload.get("issue_date")
    completion_date_str = payload.get("completion_date")
    signatory_name = payload.get("signatory_name")
    signatory_designation = payload.get("signatory_designation")
    recipients = payload.get("recipients", [])

    if not course_name or not issue_date_str:
        return jsonify({"success": False, "error": "course_name and issue_date are required"}), 400

    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"success": False, "error": "Invalid issue_date format (YYYY-MM-DD required)"}), 400

    completion_date = None
    if completion_date_str:
        try:
            completion_date = datetime.strptime(completion_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    org, err = resolve_organization(
        organization_id=payload.get("organization_id"),
        new_org_name=payload.get("new_organization_name"),
    )
    if err:
        return jsonify({"success": False, "error": err}), 400

    max_rec = current_app.config.get("MAX_RECIPIENTS_PER_JOB", 1000)
    job, job_err = create_bulk_generation_job(
        organization=org,
        course_name=course_name,
        certificate_title=certificate_title,
        issue_date=issue_date,
        completion_date=completion_date,
        signatory_name=signatory_name,
        signatory_designation=signatory_designation,
        recipients=recipients,
        source_type="manual",
        max_recipients=max_rec,
    )

    if job_err:
        return jsonify({"success": False, "error": job_err}), 400

    return jsonify({"success": True, "data": job.to_dict()}), 201


@api_bp.route("/jobs/csv", methods=["POST"])
def api_create_job_csv():
    if "csv_file" not in request.files:
        return jsonify({"success": False, "error": "csv_file is required in multipart/form-data"}), 400

    file = request.files["csv_file"]
    course_name = request.form.get("course_name")
    certificate_title = request.form.get("certificate_title", "Certificate of Completion")
    issue_date_str = request.form.get("issue_date")
    completion_date_str = request.form.get("completion_date")
    signatory_name = request.form.get("signatory_name")
    signatory_designation = request.form.get("signatory_designation")

    if not course_name or not issue_date_str:
        return jsonify({"success": False, "error": "course_name and issue_date are required"}), 400

    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"success": False, "error": "Invalid issue_date format"}), 400

    completion_date = None
    if completion_date_str:
        try:
            completion_date = datetime.strptime(completion_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    org_id = request.form.get("organization_id", type=int)
    new_org_name = request.form.get("new_organization_name")
    org, err = resolve_organization(organization_id=org_id, new_org_name=new_org_name)
    if err:
        return jsonify({"success": False, "error": err}), 400

    max_rec = current_app.config.get("MAX_RECIPIENTS_PER_JOB", 1000)
    parsed = parse_and_validate_csv(file.read(), max_recipients=max_rec)
    if not parsed.get("success"):
        return jsonify({"success": False, "error": parsed.get("error")}), 400

    valid_recipients = parsed.get("valid_rows", [])
    if not valid_recipients:
        return jsonify({"success": False, "error": "No valid recipients found in uploaded CSV", "validation": parsed}), 400

    job, job_err = create_bulk_generation_job(
        organization=org,
        course_name=course_name,
        certificate_title=certificate_title,
        issue_date=issue_date,
        completion_date=completion_date,
        signatory_name=signatory_name,
        signatory_designation=signatory_designation,
        recipients=valid_recipients,
        source_type="csv",
        max_recipients=max_rec,
    )

    if job_err:
        return jsonify({"success": False, "error": job_err}), 400

    return jsonify({
        "success": True,
        "data": job.to_dict(),
        "parsed_summary": {
            "total_rows": parsed["total_rows"],
            "valid_count": parsed["valid_count"],
            "invalid_count": parsed["invalid_count"],
        },
    }), 201


@api_bp.route("/jobs/<int:job_id>/retry", methods=["POST"])
def api_retry_job(job_id: int):
    job = db.session.get(GenerationJob, job_id)
    if not job:
        return jsonify({"success": False, "error": f"Job #{job_id} not found"}), 404

    failed_count = Certificate.query.filter_by(job_id=job.id, status="Failed").count()
    if failed_count == 0:
        return jsonify({"success": False, "error": "No failed certificates to retry"}), 400

    enqueue_retry_job(job.id)
    return jsonify({"success": True, "message": f"Retry enqueued for {failed_count} certificates."})


@api_bp.route("/jobs/<int:job_id>/download-zip", methods=["GET"])
def api_download_zip(job_id: int):
    zip_path, err, count = create_job_certificates_zip(job_id)
    if err or not zip_path:
        return jsonify({"success": False, "error": err or "ZIP file could not be generated"}), 404

    return send_file(
        str(zip_path),
        mimetype="application/zip",
        as_attachment=True,
        download_name=zip_path.name,
    )


@api_bp.route("/certificates", methods=["GET"])
def api_list_certificates():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status")

    query = Certificate.query
    if search:
        query = query.filter(
            db.or_(
                Certificate.recipient_name.ilike(f"%{search}%"),
                Certificate.recipient_email.ilike(f"%{search}%"),
                Certificate.certificate_code.ilike(f"%{search}%"),
            )
        )
    if status_filter:
        query = query.filter(Certificate.status == status_filter)

    pagination = query.order_by(Certificate.id.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "data": [c.to_dict() for c in pagination.items],
    })


@api_bp.route("/certificates/<int:cert_id>", methods=["GET"])
def api_get_certificate(cert_id: int):
    cert = db.session.get(Certificate, cert_id)
    if not cert:
        return jsonify({"success": False, "error": f"Certificate #{cert_id} not found"}), 404

    return jsonify({"success": True, "data": cert.to_dict()})


@api_bp.route("/certificates/<int:cert_id>/download", methods=["GET"])
def api_download_certificate(cert_id: int):
    cert = db.session.get(Certificate, cert_id)
    if not cert:
        return jsonify({"success": False, "error": f"Certificate #{cert_id} not found"}), 404

    if cert.status != "Completed" or not cert.file_path:
        return jsonify({"success": False, "error": f"Certificate is not completed (status: {cert.status})"}), 400

    safe_filename = os.path.basename(cert.file_path)
    file_path = (GENERATED_DIR / safe_filename).resolve()

    if not str(file_path).startswith(str(GENERATED_DIR.resolve())) or not file_path.exists():
        return jsonify({"success": False, "error": "PDF file not found on disk"}), 404

    return send_file(
        str(file_path),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{cert.certificate_code}.pdf",
    )


@api_bp.route("/activity", methods=["GET"])
def api_list_activity():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    event_type = request.args.get("event_type")

    query = ActivityLog.query
    if event_type:
        query = query.filter(ActivityLog.event_type == event_type)

    pagination = query.order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "success": True,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "data": [log.to_dict() for log in pagination.items],
    })


@api_bp.route("/auth/register", methods=["POST"])
def api_auth_register():
    payload = request.get_json() or {}
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not name or not email or not password:
        return jsonify({"success": False, "error": "name, email, and password are required"}), 400

    if len(password) < 6:
        return jsonify({"success": False, "error": "password must be at least 6 characters"}), 400

    from models.user import User
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"success": False, "error": "email already registered"}), 400

    user = User(name=name, email=email, role="operator", is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"success": True, "message": "User registered successfully", "user": user.to_dict()}), 201


@api_bp.route("/auth/login", methods=["POST"])
def api_auth_login():
    payload = request.get_json() or {}
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "error": "email and password are required"}), 400

    from models.user import User
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid email or password"}), 401

    if not user.is_active:
        return jsonify({"success": False, "error": "Account deactivated"}), 403

    return jsonify({"success": True, "message": "Authenticated successfully", "user": user.to_dict()})
