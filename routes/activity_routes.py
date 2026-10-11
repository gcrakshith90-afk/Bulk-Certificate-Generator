from datetime import datetime
from flask import Blueprint, render_template, request
from extensions import db
from models.activity_log import ActivityLog
from routes.auth_routes import login_required

activity_bp = Blueprint("activity", __name__, url_prefix="/activity-logs")


@activity_bp.route("", methods=["GET"])
@login_required
def list_logs():
    event_type = request.args.get("event_type", "").strip()
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = ActivityLog.query

    if event_type:
        query = query.filter(ActivityLog.event_type == event_type)

    if search:
        query = query.filter(ActivityLog.description.ilike(f"%{search}%"))

    if date_from:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(ActivityLog.created_at >= d_from)
        except Exception:
            pass

    if date_to:
        try:
            d_to = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(ActivityLog.created_at <= d_to.replace(hour=23, minute=59, second=59))
        except Exception:
            pass

    pagination = query.order_by(ActivityLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    distinct_events = [e[0] for e in db.session.query(ActivityLog.event_type).distinct().all()]

    return render_template(
        "activity_logs.html",
        logs=pagination.items,
        pagination=pagination,
        distinct_events=distinct_events,
        event_type=event_type,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
