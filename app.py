import os
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify

from config import config_by_name
from extensions import db, migrate, csrf
from models import User, Organization, GenerationJob, Certificate, ActivityLog
from routes.auth_routes import auth_bp, get_current_user
from routes.dashboard_routes import dashboard_bp
from routes.organization_routes import org_bp
from routes.bulk_routes import bulk_bp
from routes.job_routes import job_bp
from routes.certificate_routes import cert_bp
from routes.activity_routes import activity_bp
from routes.api_routes import api_bp
from tasks.certificate_tasks import start_background_worker


def create_app(config_name: str = None) -> Flask:
    """CertiFlow Application Factory."""
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_cls = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_cls)

    # Ensure required directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["GENERATED_CERTIFICATES_FOLDER"], exist_ok=True)
    os.makedirs(app.config["TEMP_ZIPS_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(org_bp)
    app.register_blueprint(bulk_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(cert_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(api_bp)

    # Inject context processors for templates
    @app.context_processor
    def inject_template_globals():
        return {
            "current_user": get_current_user(),
            "current_year": datetime.now(timezone.utc).year,
        }

    # Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": getattr(e, "description", "Bad Request")}), 400
        return render_template("errors/400.html", error_description=getattr(e, "description", None)), 400

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": getattr(e, "description", "Access Forbidden")}), 403
        return render_template("errors/403.html", error_description=getattr(e, "description", None)), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": getattr(e, "description", "Resource Not Found")}), 404
        return render_template("errors/404.html", error_description=getattr(e, "description", None)), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal Server Error"}), 500
        return render_template("errors/500.html"), 500

    # Initialize database tables and seeds in non-testing mode
    with app.app_context():
        db.create_all()
        seed_initial_data(app)

    # Start the isolated background task worker thread (skip during testing if desired)
    if not app.config.get("TESTING"):
        start_background_worker(app)

    return app


def seed_initial_data(app: Flask):
    """Safely seed initial administrator account and organizations if database is fresh."""
    try:
        # 1. Admin user
        admin_email = app.config.get("ADMIN_EMAIL", "admin@certiflow.local").lower()
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                name=app.config.get("ADMIN_NAME", "CertiFlow Admin"),
                email=admin_email,
                role="admin",
                is_active=True,
            )
            admin.set_password(app.config.get("ADMIN_PASSWORD", "Admin@123456"))
            db.session.add(admin)

        # 2. Sample Organizations if none exist
        if Organization.query.count() == 0:
            org1 = Organization(
                name="Stanford Engineering Academy",
                organization_type="university",
                contact_person="Dr. Eleanor Vance",
                contact_email="admissions@stanford-academy.edu",
                phone="+1 (650) 723-2300",
                address="450 Jane Stanford Way, Stanford, CA 94305",
                is_active=True,
            )
            org2 = Organization(
                name="TechPulse Global Institute",
                organization_type="company",
                contact_person="Marcus Vance",
                contact_email="certifications@techpulse.io",
                phone="+1 (415) 555-0199",
                address="100 Market St, San Francisco, CA 94105",
                is_active=True,
            )
            db.session.add_all([org1, org2])

            log = ActivityLog(
                event_type="SYSTEM_INITIALIZED",
                description="Database seeded with initial administrative profile and sample organizations.",
            )
            db.session.add(log)

        db.session.commit()
    except Exception as e:
        db.session.rollback()


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
