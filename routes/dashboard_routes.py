from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, request, current_app
from extensions import db
from models.generation_job import GenerationJob
from models.activity_log import ActivityLog
from routes.auth_routes import login_required, get_current_user
from services.dashboard_service import get_dashboard_statistics

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def index():
    start_str = request.args.get("start_date", "").strip()
    end_str = request.args.get("end_date", "").strip()

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
    recent_jobs = GenerationJob.query.order_by(GenerationJob.created_at.desc()).limit(6).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_jobs=recent_jobs,
        recent_activities=recent_activities,
        start_date=start_str,
        end_date=end_str,
    )


@dashboard_bp.route("/settings", methods=["GET"])
@login_required
def settings():
    user = get_current_user()
    app_config = {
        "max_content_length": f"{current_app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024):.1f} MB",
        "max_recipients_per_job": current_app.config.get("MAX_RECIPIENTS_PER_JOB", 1000),
        "db_uri": current_app.config.get("SQLALCHEMY_DATABASE_URI"),
        "upload_folder": str(current_app.config.get("UPLOAD_FOLDER")),
        "output_folder": str(current_app.config.get("GENERATED_CERTIFICATES_FOLDER")),
        "temp_zips_folder": str(current_app.config.get("TEMP_ZIPS_FOLDER")),
        "csrf_enabled": current_app.config.get("WTF_CSRF_ENABLED", True),
    }
    return render_template("settings.html", user=user, app_config=app_config)
