from models import User
from extensions import db


def test_login_successful(client, app):
    res = client.post("/login", data={"email": "admin@test.local", "password": "AdminPass123"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome back, Test Admin!" in res.data


def test_login_invalid_password(client, app):
    res = client.post("/login", data={"email": "admin@test.local", "password": "WrongPassword"})
    assert res.status_code == 200
    assert b"Invalid email or password" in res.data


def test_login_inactive_user(client, app):
    with app.app_context():
        user = User.query.filter_by(email="operator@test.local").first()
        user.is_active = False
        db.session.commit()

    res = client.post("/login", data={"email": "operator@test.local", "password": "OperatorPass123"})
    assert res.status_code == 200
    assert b"This account is currently deactivated" in res.data


def test_protected_route_requires_login(client):
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_logout(admin_client):
    res = admin_client.post("/logout", follow_redirects=True)
    assert res.status_code == 200
    assert b"You have been signed out safely" in res.data


def test_user_registration_success(client, app):
    payload = {
        "name": "Jane User",
        "email": "jane.user@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    }
    res = client.post("/register", data=payload, follow_redirects=True)
    assert res.status_code == 200
    assert b"Welcome to CertiFlow, Jane User!" in res.data
    with app.app_context():
        u = User.query.filter_by(email="jane.user@example.com").first()
        assert u is not None
        assert u.name == "Jane User"
        assert u.check_password("Password123")


def test_user_registration_password_mismatch(client, app):
    payload = {
        "name": "Mismatch User",
        "email": "mismatch@example.com",
        "password": "Password123",
        "confirm_password": "DifferentPassword",
    }
    res = client.post("/register", data=payload)
    assert res.status_code == 200
    assert b"Passwords do not match" in res.data


def test_user_registration_duplicate_email(client, app):
    payload = {
        "name": "Duplicate User",
        "email": "admin@test.local",  # Already exists
        "password": "Password123",
        "confirm_password": "Password123",
    }
    res = client.post("/register", data=payload, follow_redirects=True)
    assert res.status_code == 200
    assert b"An account with this email address already exists" in res.data


def test_login_with_newly_created_credentials(client, app):
    # First register
    payload = {
        "name": "Custom User",
        "email": "custom.user@example.com",
        "password": "MySecretPass999",
        "confirm_password": "MySecretPass999",
    }
    client.post("/register", data=payload)
    client.post("/logout")  # Log out

    # Now log in using the newly created credentials
    login_res = client.post(
        "/login",
        data={"email": "custom.user@example.com", "password": "MySecretPass999"},
        follow_redirects=True,
    )
    assert login_res.status_code == 200
    assert b"Welcome back, Custom User!" in login_res.data
