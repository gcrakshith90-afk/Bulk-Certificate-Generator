import os
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, abort, flash, redirect, url_for, current_app
from extensions import db
from models.certificate import Certificate
from models.generation_job import GenerationJob
from models.organization import Organization
from models.activity_log import ActivityLog
from routes.auth_routes import login_required, get_current_user

cert_bp = Blueprint("certificates", __name__, url_prefix="/certificates")

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated_certificates"


@cert_bp.route("", methods=["GET"])
@login_required
def list_certificates():
    search = request.args.get("search", "").strip()
    org_filter = request.args.get("org_id", type=int)
    course_filter = request.args.get("course", "").strip()
    status_filter = request.args.get("status", "").strip()
    issue_from = request.args.get("issue_from", "").strip()
    issue_to = request.args.get("issue_to", "").strip()
    created_from = request.args.get("created_from", "").strip()
    created_to = request.args.get("created_to", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = (
        Certificate.query.join(GenerationJob, Certificate.job_id == GenerationJob.id)
        .join(Organization, GenerationJob.organization_id == Organization.id)
    )

    if search:
        query = query.filter(
            db.or_(
                Certificate.recipient_name.ilike(f"%{search}%"),
                Certificate.recipient_email.ilike(f"%{search}%"),
                Certificate.certificate_code.ilike(f"%{search}%"),
            )
        )

    if org_filter:
        query = query.filter(GenerationJob.organization_id == org_filter)

    if course_filter:
        query = query.filter(GenerationJob.course_name.ilike(f"%{course_filter}%"))

    if status_filter:
        query = query.filter(Certificate.status == status_filter)

    if issue_from:
        try:
            d_from = datetime.strptime(issue_from, "%Y-%m-%d").date()
            query = query.filter(GenerationJob.issue_date >= d_from)
        except Exception:
            pass

    if issue_to:
        try:
            d_to = datetime.strptime(issue_to, "%Y-%m-%d").date()
            query = query.filter(GenerationJob.issue_date <= d_to)
        except Exception:
            pass

    if created_from:
        try:
            c_from = datetime.strptime(created_from, "%Y-%m-%d")
            query = query.filter(Certificate.created_at >= c_from)
        except Exception:
            pass

    if created_to:
        try:
            c_to = datetime.strptime(created_to, "%Y-%m-%d")
            query = query.filter(Certificate.created_at <= c_to.replace(hour=23, minute=59, second=59))
        except Exception:
            pass

    pagination = query.order_by(Certificate.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    organizations = Organization.query.order_by(Organization.name.asc()).all()

    return render_template(
        "certificates.html",
        certificates=pagination.items,
        pagination=pagination,
        organizations=organizations,
        search=search,
        org_filter=org_filter,
        course_filter=course_filter,
        status_filter=status_filter,
        issue_from=issue_from,
        issue_to=issue_to,
        created_from=created_from,
        created_to=created_to,
    )


@cert_bp.route("/<int:cert_id>", methods=["GET"])
@login_required
def view_certificate(cert_id: int):
    cert = db.session.get(Certificate, cert_id)
    if not cert:
        abort(404, description=f"Certificate #{cert_id} not found.")

    return render_template("certificate_details.html", cert=cert)


@cert_bp.route("/<int:cert_id>/download", methods=["GET"])
@login_required
def download_certificate(cert_id: int):
    cert = db.session.get(Certificate, cert_id)
    if not cert:
        abort(404, description=f"Certificate #{cert_id} not found.")

    if cert.status != "Completed" or not cert.file_path:
        flash(f"Certificate #{cert.certificate_code} has status '{cert.status}' and cannot be downloaded.", "warning")
        return redirect(url_for("certificates.view_certificate", cert_id=cert.id))

    # Path traversal safety
    safe_filename = os.path.basename(cert.file_path)
    file_path = (GENERATED_DIR / safe_filename).resolve()

    if not str(file_path).startswith(str(GENERATED_DIR.resolve())) or not file_path.exists():
        abort(404, description="The requested certificate PDF file was not found on disk.")

    user = get_current_user()
    log = ActivityLog(
        user_id=user.id if user else None,
        job_id=cert.job_id,
        certificate_id=cert.id,
        event_type="CERTIFICATE_DOWNLOADED",
        description=f"Downloaded PDF for certificate {cert.certificate_code} ({cert.recipient_name}).",
    )
    db.session.add(log)
    db.session.commit()

    download_name = f"{cert.certificate_code}_{cert.recipient_name.replace(' ', '_')}.pdf"
    return send_file(
        str(file_path),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )
