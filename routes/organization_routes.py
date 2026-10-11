from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from extensions import db
from models.organization import Organization
from models.generation_job import GenerationJob
from models.activity_log import ActivityLog
from forms import OrganizationForm
from routes.auth_routes import login_required, admin_required, get_current_user

org_bp = Blueprint("organizations", __name__, url_prefix="/organizations")


@org_bp.route("", methods=["GET"])
@login_required
def list_orgs():
    search = request.args.get("search", "").strip()
    org_type = request.args.get("type", "").strip()
    status_filter = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = Organization.query

    if search:
        query = query.filter(
            db.or_(
                Organization.name.ilike(f"%{search}%"),
                Organization.contact_person.ilike(f"%{search}%"),
                Organization.contact_email.ilike(f"%{search}%"),
            )
        )

    if org_type:
        query = query.filter(Organization.organization_type == org_type)

    if status_filter == "active":
        query = query.filter(Organization.is_active.is_(True))
    elif status_filter == "inactive":
        query = query.filter(Organization.is_active.is_(False))

    pagination = query.order_by(Organization.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "organizations.html",
        organizations=pagination.items,
        pagination=pagination,
        search=search,
        selected_type=org_type,
        selected_status=status_filter,
    )


@org_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_org():
    form = OrganizationForm()
    user = get_current_user()

    if form.validate_on_submit():
        existing = Organization.query.filter(db.func.lower(Organization.name) == form.name.data.strip().lower()).first()
        if existing:
            flash(f"An organization with the name '{form.name.data.strip()}' already exists.", "warning")
            return render_template("organization_form.html", form=form, title="Add Organization", is_edit=False)

        org = Organization(
            name=form.name.data.strip(),
            organization_type=form.organization_type.data,
            contact_person=form.contact_person.data.strip(),
            contact_email=form.contact_email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            address=form.address.data.strip() if form.address.data else None,
            is_active=form.is_active.data,
        )
        db.session.add(org)
        db.session.flush()

        log = ActivityLog(
            user_id=user.id if user else None,
            event_type="ORGANIZATION_CREATED",
            description=f"Created organization '{org.name}' ({org.organization_type}).",
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Organization '{org.name}' created successfully.", "success")
        return redirect(url_for("organizations.view_org", org_id=org.id))

    return render_template("organization_form.html", form=form, title="Add Organization", is_edit=False)


@org_bp.route("/<int:org_id>", methods=["GET"])
@login_required
def view_org(org_id: int):
    org = db.session.get(Organization, org_id)
    if not org:
        abort(404, description="Organization not found")

    recent_jobs = org.jobs.order_by(GenerationJob.created_at.desc()).limit(10).all()
    return render_template("organization_details.html", org=org, recent_jobs=recent_jobs)


@org_bp.route("/<int:org_id>/edit", methods=["GET", "POST"])
@login_required
def edit_org(org_id: int):
    org = db.session.get(Organization, org_id)
    if not org:
        abort(404, description="Organization not found")

    form = OrganizationForm(obj=org)
    user = get_current_user()

    if form.validate_on_submit():
        existing = Organization.query.filter(
            db.func.lower(Organization.name) == form.name.data.strip().lower(),
            Organization.id != org.id,
        ).first()
        if existing:
            flash(f"Another organization is already named '{form.name.data.strip()}'.", "warning")
            return render_template("organization_form.html", form=form, title=f"Edit {org.name}", is_edit=True, org=org)

        org.name = form.name.data.strip()
        org.organization_type = form.organization_type.data
        org.contact_person = form.contact_person.data.strip()
        org.contact_email = form.contact_email.data.strip().lower()
        org.phone = form.phone.data.strip() if form.phone.data else None
        org.address = form.address.data.strip() if form.address.data else None
        org.is_active = form.is_active.data

        log = ActivityLog(
            user_id=user.id if user else None,
            event_type="ORGANIZATION_UPDATED",
            description=f"Updated organization details for '{org.name}'.",
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Organization '{org.name}' updated successfully.", "success")
        return redirect(url_for("organizations.view_org", org_id=org.id))

    return render_template("organization_form.html", form=form, title=f"Edit {org.name}", is_edit=True, org=org)


@org_bp.route("/<int:org_id>/toggle-status", methods=["POST"])
@login_required
def toggle_status(org_id: int):
    org = db.session.get(Organization, org_id)
    if not org:
        abort(404, description="Organization not found")

    user = get_current_user()
    org.is_active = not org.is_active

    action_name = "activated" if org.is_active else "deactivated"
    log = ActivityLog(
        user_id=user.id if user else None,
        event_type="ORGANIZATION_STATUS_CHANGED",
        description=f"Organization '{org.name}' was {action_name}.",
    )
    db.session.add(log)
    db.session.commit()

    flash(f"Organization '{org.name}' has been {action_name}.", "info")
    return redirect(request.referrer or url_for("organizations.list_orgs"))
