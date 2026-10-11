import io
from services.csv_service import parse_and_validate_csv, sanitize_cell_value
from models import Organization, GenerationJob, Certificate
from extensions import db


def test_sanitize_csv_formula_injection():
    assert sanitize_cell_value("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    assert sanitize_cell_value("+12345") == "'+12345"
    assert sanitize_cell_value("-500") == "'-500"
    assert sanitize_cell_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_cell_value("Normal Recipient") == "Normal Recipient"


def test_parse_valid_csv():
    csv_data = b"name,email\nAlice,alice@example.com\nBob,bob@example.com\nCharlie,charlie@example.org\n"
    res = parse_and_validate_csv(csv_data)
    assert res["success"] is True
    assert res["total_rows"] == 3
    assert res["valid_count"] == 3
    assert res["invalid_count"] == 0


def test_parse_csv_missing_header():
    csv_data = b"fullname,contact\nAlice,alice@example.com\n"
    res = parse_and_validate_csv(csv_data)
    assert res["success"] is False
    assert "Missing required columns" in res["error"]


def test_parse_csv_with_invalid_and_duplicate_rows():
    csv_data = (
        b"name,email\n"
        b"Valid One,one@example.com\n"
        b",missing_name@example.com\n"
        b"Bad Email,not-an-email\n"
        b"Duplicate One,one@example.com\n"
    )
    res = parse_and_validate_csv(csv_data)
    assert res["success"] is True
    assert res["total_rows"] == 4
    assert res["valid_count"] == 1
    assert res["invalid_count"] == 3
    assert len(res["invalid_rows"]) == 3


def test_csv_upload_and_preview_workflow(admin_client, app):
    with app.app_context():
        org = Organization.query.first()
        org_id = org.id

    csv_bytes = b"name,email\nRecipient One,r1@example.com\nRecipient Two,r2@example.com\n"
    data = {
        "organization_id": org_id,
        "course_name": "Data Science Masterclass",
        "certificate_title": "Certificate of Excellence",
        "issue_date": "2026-10-15",
        "csv_file": (io.BytesIO(csv_bytes), "students.csv"),
    }

    res = admin_client.post("/bulk-generation/csv/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert b"CSV Recipients Preview" in res.data
    assert b"Recipient One" in res.data
    assert b"Recipient Two" in res.data
