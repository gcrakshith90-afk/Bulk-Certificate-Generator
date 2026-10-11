import json
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, jsonify, session
from extensions import db
from models.organization import Organization
from models.activity_log import ActivityLog
from forms import CSVUploadForm
from routes.auth_routes import login_required, get_current_user
from services.csv_service import parse_and_validate_csv
from services.bulk_service import resolve_organization, create_bulk_generation_job
from services.certificate_service import render_certificate_html

bulk_bp = Blueprint("bulk", __name__, url_prefix="/bulk-generation")


@bulk_bp.route("", methods=["GET"])
@login_required
def generate():
    orgs = Organization.query.filter_by(is_active=True).order_by(Organization.name.asc()).all()
    selected_org_id = request.args.get("org_id", type=int)
    today = date.today().isoformat()
    return render_template(
        "bulk_generation.html",
        organizations=orgs,
        selected_org_id=selected_org_id,
        today=today,
    )


@bulk_bp.route("/sample-csv", methods=["GET"])
@login_required
def download_sample_csv():
    """Provide downloadable sample CSV file."""
    csv_content = "name,email\nRakshith,rakshith@example.com\nPriya,priya@example.com\nArun,arun@example.com\nDeepa Sharma,deepa.sharma@example.org\nKavita Patel,kavita.patel@example.com\n"
    from io import BytesIO
    return send_file(
        BytesIO(csv_content.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="sample_recipients.csv",
    )


@bulk_bp.route("/manual", methods=["POST"])
@login_required
def submit_manual():
    user = get_current_user()
    org_id = request.form.get("organization_id", type=int)
    new_org_name = request.form.get("new_organization_name", "").strip()
    course_name = request.form.get("course_name", "").strip()
    certificate_title = request.form.get("certificate_title", "").strip() or "Certificate of Completion"
    issue_date_str = request.form.get("issue_date", "").strip()
    completion_date_str = request.form.get("completion_date", "").strip()
    signatory_name = request.form.get("signatory_name", "").strip()
    signatory_designation = request.form.get("signatory_designation", "").strip()

    # Dates
    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
    except Exception:
        flash("Invalid issue date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for("bulk.generate"))

    completion_date = None
    if completion_date_str:
        try:
            completion_date = datetime.strptime(completion_date_str, "%Y-%m-%d").date()
        except Exception:
            flash("Invalid completion date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for("bulk.generate"))

    # Parse recipients array from JSON or form lists
    recipients_json = request.form.get("recipients_json")
    recipients = []
    if recipients_json:
        try:
            recipients = json.loads(recipients_json)
        except Exception:
            flash("Invalid recipient format submitted.", "danger")
            return redirect(url_for("bulk.generate"))
    else:
        # Fallback to direct field parsing
        names = request.form.getlist("recipient_name[]")
        emails = request.form.getlist("recipient_email[]")
        for n, e in zip(names, emails):
            if n.strip() or e.strip():
                recipients.append({"name": n.strip(), "email": e.strip()})

    if not recipients:
        flash("Please enter at least one recipient.", "warning")
        return redirect(url_for("bulk.generate"))

    # Resolve organization
    org, err = resolve_organization(
        organization_id=org_id,
        new_org_name=new_org_name,
        contact_person=user.name if user else "Admin",
        contact_email=user.email if user else "admin@certiflow.local",
    )
    if err:
        flash(err, "danger")
        return redirect(url_for("bulk.generate"))

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
        created_by=user.id if user else None,
        max_recipients=max_rec,
    )

    if job_err:
        flash(job_err, "danger")
        return redirect(url_for("bulk.generate"))

    flash(f"Bulk Generation Job #{job.id} created successfully with {job.total} recipients! Generation has started in the background.", "success")
    return redirect(url_for("jobs.view_job", job_id=job.id))


@bulk_bp.route("/csv/upload", methods=["POST"])
@login_required
def upload_csv():
    user = get_current_user()
    if "csv_file" not in request.files:
        flash("No file was uploaded.", "danger")
        return redirect(url_for("bulk.generate"))

    file = request.files["csv_file"]
    if not file or not file.filename.lower().endswith(".csv"):
        flash("Please upload a valid .csv file.", "danger")
        return redirect(url_for("bulk.generate"))

    org_id = request.form.get("organization_id", type=int)
    new_org_name = request.form.get("new_organization_name", "").strip()
    course_name = request.form.get("course_name", "").strip()
    certificate_title = request.form.get("certificate_title", "").strip() or "Certificate of Completion"
    issue_date_str = request.form.get("issue_date", "").strip()
    completion_date_str = request.form.get("completion_date", "").strip()
    signatory_name = request.form.get("signatory_name", "").strip()
    signatory_designation = request.form.get("signatory_designation", "").strip()

    if not course_name:
        flash("Course or event name is required.", "danger")
        return redirect(url_for("bulk.generate"))

    if not issue_date_str:
        flash("Issue date is required.", "danger")
        return redirect(url_for("bulk.generate"))

    # Resolve organization
    org, err = resolve_organization(
        organization_id=org_id,
        new_org_name=new_org_name,
        contact_person=user.name if user else "Admin",
        contact_email=user.email if user else "admin@certiflow.local",
    )
    if err:
        flash(err, "danger")
        return redirect(url_for("bulk.generate"))

    # Read and parse CSV
    file_bytes = file.read()
    max_rec = current_app.config.get("MAX_RECIPIENTS_PER_JOB", 1000)
    parsed_result = parse_and_validate_csv(file_bytes, max_recipients=max_rec)

    if not parsed_result.get("success"):
        flash(f"CSV parsing error: {parsed_result.get('error')}", "danger")
        return redirect(url_for("bulk.generate"))

    # Log CSV upload
    log = ActivityLog(
        user_id=user.id if user else None,
        event_type="CSV_UPLOADED",
        description=f"Uploaded CSV '{file.filename}' containing {parsed_result['total_rows']} recipient rows for organization '{org.name}'.",
    )
    db.session.add(log)
    db.session.commit()

    # Pass to Preview template
    return render_template(
        "csv_preview.html",
        organization=org,
        course_name=course_name,
        certificate_title=certificate_title,
        issue_date=issue_date_str,
        completion_date=completion_date_str,
        signatory_name=signatory_name,
        signatory_designation=signatory_designation,
        filename=file.filename,
        parsed_result=parsed_result,
    )


@bulk_bp.route("/csv/confirm", methods=["POST"])
@login_required
def confirm_csv():
    user = get_current_user()
    org_id = request.form.get("organization_id", type=int)
    course_name = request.form.get("course_name", "").strip()
    certificate_title = request.form.get("certificate_title", "").strip() or "Certificate of Completion"
    issue_date_str = request.form.get("issue_date", "").strip()
    completion_date_str = request.form.get("completion_date", "").strip()
    signatory_name = request.form.get("signatory_name", "").strip()
    signatory_designation = request.form.get("signatory_designation", "").strip()

    recipients_json = request.form.get("recipients_json", "[]")
    try:
        recipients = json.loads(recipients_json)
    except Exception:
        flash("Invalid recipient data.", "danger")
        return redirect(url_for("bulk.generate"))

    if not recipients:
        flash("No valid recipients selected to generate certificates.", "warning")
        return redirect(url_for("bulk.generate"))

    org = db.session.get(Organization, org_id)
    if not org or not org.is_active:
        flash("Invalid or inactive organization selected.", "danger")
        return redirect(url_for("bulk.generate"))

    try:
        issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
    except Exception:
        flash("Invalid issue date format.", "danger")
        return redirect(url_for("bulk.generate"))

    completion_date = None
    if completion_date_str:
        try:
            completion_date = datetime.strptime(completion_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    max_rec = current_app.config.get("MAX_RECIPIENTS_PER_JOB", 1000)
    job, err = create_bulk_generation_job(
        organization=org,
        course_name=course_name,
        certificate_title=certificate_title,
        issue_date=issue_date,
        completion_date=completion_date,
        signatory_name=signatory_name,
        signatory_designation=signatory_designation,
        recipients=recipients,
        source_type="csv",
        created_by=user.id if user else None,
        max_recipients=max_rec,
    )

    if err:
        flash(err, "danger")
        return redirect(url_for("bulk.generate"))

    flash(f"Bulk Generation Job #{job.id} started successfully with {job.total} recipients from CSV!", "success")
    return redirect(url_for("jobs.view_job", job_id=job.id))


@bulk_bp.route("/preview-html", methods=["POST"])
@login_required
def preview_html():
    """Render a live HTML preview of the certificate."""
    data = request.get_json() or {}
    rendered = render_certificate_html(
        organization_name=data.get("organization_name", "Acme University"),
        certificate_title=data.get("certificate_title", "Certificate of Completion"),
        recipient_name=data.get("recipient_name", "Jane Doe"),
        recipient_email=data.get("recipient_email", "jane.doe@example.com"),
        course_name=data.get("course_name", "Advanced Full-Stack Engineering"),
        issue_date=date.today(),
        completion_date=date.today(),
        signatory_name=data.get("signatory_name", "Dr. Jane Smith"),
        signatory_designation=data.get("signatory_designation", "Director of Certification"),
        certificate_code="CERT-2026-PREVIEW01",
    )
    return jsonify({"success": True, "html": rendered})
