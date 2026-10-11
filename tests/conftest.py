import os
import shutil
import tempfile
from pathlib import Path
import pytest
from app import create_app
from extensions import db
from models import User, Organization, GenerationJob, Certificate, ActivityLog


@pytest.fixture(scope="session")
def test_temp_dir():
    temp_dir = Path(tempfile.mkdtemp(prefix="certiflow_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def app(test_temp_dir):
    # Setup test app
    app = create_app(config_name="testing")
    app.config["UPLOAD_FOLDER"] = test_temp_dir / "uploads"
    app.config["GENERATED_CERTIFICATES_FOLDER"] = test_temp_dir / "generated_certificates"
    app.config["TEMP_ZIPS_FOLDER"] = test_temp_dir / "temp_zips"
    
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["GENERATED_CERTIFICATES_FOLDER"], exist_ok=True)
    os.makedirs(app.config["TEMP_ZIPS_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()
        # Ensure test users
        admin = User(name="Test Admin", email="admin@test.local", role="admin", is_active=True)
        admin.set_password("AdminPass123")
        operator = User(name="Test Operator", email="operator@test.local", role="operator", is_active=True)
        operator.set_password("OperatorPass123")
        db.session.add_all([admin, operator])

        # Ensure test org
        org = Organization(
            name="Apex Institute of Technology",
            organization_type="college",
            contact_person="Prof. Allen",
            contact_email="allen@apex.edu",
            is_active=True,
        )
        db.session.add(org)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(app, client):
    with client.session_transaction() as sess:
        with app.app_context():
            admin = User.query.filter_by(email="admin@test.local").first()
            sess["user_id"] = admin.id
            sess["user_name"] = admin.name
            sess["user_email"] = admin.email
            sess["user_role"] = admin.role
    return client


@pytest.fixture
def operator_client(app, client):
    with client.session_transaction() as sess:
        with app.app_context():
            op = User.query.filter_by(email="operator@test.local").first()
            sess["user_id"] = op.id
            sess["user_name"] = op.name
            sess["user_email"] = op.email
            sess["user_role"] = op.role
    return client
