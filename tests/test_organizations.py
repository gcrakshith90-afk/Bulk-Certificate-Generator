from models import Organization
from extensions import db


def test_list_organizations(admin_client):
    res = admin_client.get("/organizations")
    assert res.status_code == 200
    assert b"Apex Institute of Technology" in res.data


def test_create_organization_success(admin_client, app):
    payload = {
        "name": "Global Tech University",
        "organization_type": "university",
        "contact_person": "Dean Robert",
        "contact_email": "dean@gtu.edu",
        "phone": "+1 555-1234",
        "address": "Campus Drive",
        "is_active": "y",
    }
    res = admin_client.post("/organizations/new", data=payload, follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        org = Organization.query.filter_by(name="Global Tech University").first()
        assert org is not None
        assert org.contact_email == "dean@gtu.edu"


def test_prevent_duplicate_organization_name(admin_client, app):
    payload = {
        "name": "Apex Institute of Technology",  # Duplicate name
        "organization_type": "college",
        "contact_person": "Copycat",
        "contact_email": "copycat@apex.edu",
    }
    res = admin_client.post("/organizations/new", data=payload, follow_redirects=True)
    assert res.status_code == 200
    assert b"already exists" in res.data


def test_edit_organization(admin_client, app):
    with app.app_context():
        org = Organization.query.filter_by(name="Apex Institute of Technology").first()
        org_id = org.id

    payload = {
        "name": "Apex Institute of Advanced Technology",
        "organization_type": "university",
        "contact_person": "Prof. Allen Updated",
        "contact_email": "allen.updated@apex.edu",
        "is_active": "y",
    }
    res = admin_client.post(f"/organizations/{org_id}/edit", data=payload, follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        updated_org = db.session.get(Organization, org_id)
        assert updated_org.name == "Apex Institute of Advanced Technology"
        assert updated_org.contact_person == "Prof. Allen Updated"


def test_toggle_organization_status(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        org_id = org.id
        initial_status = org.is_active

    res = admin_client.post(f"/organizations/{org_id}/toggle-status", follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        toggled_org = db.session.get(Organization, org_id)
        assert toggled_org.is_active != initial_status
