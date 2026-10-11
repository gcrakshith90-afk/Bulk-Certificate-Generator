from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, g
from extensions import db
from models.user import User
from models.activity_log import ActivityLog

auth_bp = Blueprint("auth", __name__)


def get_current_user():
    """Retrieve currently authenticated user from session or cached in g."""
    if hasattr(g, "_current_user"):
        return g._current_user
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.is_active:
            g._current_user = user
            return user
    g._current_user = None
    return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith("/api/"):
                return {"success": False, "error": "Authentication required"}, 401
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith("/api/"):
                return {"success": False, "error": "Authentication required"}, 401
            flash("Please sign in as administrator.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        if not user.is_admin:
            if request.path.startswith("/api/"):
                return {"success": False, "error": "Administrator privileges required"}, 403
            flash("Administrator privileges required.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("This account is currently deactivated. Please contact an administrator.", "danger")
                return render_template("login.html")

            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_email"] = user.email
            session["user_role"] = user.role

            # Log login event
            log = ActivityLog(
                user_id=user.id,
                event_type="USER_LOGIN",
                description=f"User {user.name} ({user.email}) logged in successfully.",
            )
            db.session.add(log)
            db.session.commit()

            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html", name=name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", name=name, email=email)

        if password != confirm_password:
            flash("Passwords do not match. Please verify your password.", "danger")
            return render_template("register.html", name=name, email=email)

        # Check existing user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address already exists. Please sign in.", "warning")
            return redirect(url_for("auth.login", email=email))

        # Create new user credentials
        user = User(
            name=name,
            email=email,
            role="operator",
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Log registration activity
        log = ActivityLog(
            user_id=user.id,
            event_type="USER_REGISTERED",
            description=f"New user {user.name} ({user.email}) registered credentials.",
        )
        db.session.add(log)
        db.session.commit()

        # Auto-login newly registered user
        session.clear()
        session["user_id"] = user.id
        session["user_name"] = user.name
        session["user_email"] = user.email
        session["user_role"] = user.role

        flash(f"Account created successfully! Welcome to CertiFlow, {user.name}!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("register.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    user = get_current_user()
    if user:
        log = ActivityLog(
            user_id=user.id,
            event_type="USER_LOGOUT",
            description=f"User {user.name} logged out.",
        )
        db.session.add(log)
        db.session.commit()

    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("auth.login"))
