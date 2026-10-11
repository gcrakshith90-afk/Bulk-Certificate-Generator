import csv
import io
import re
from typing import Dict, Any, List

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def sanitize_cell_value(val: str) -> str:
    """Sanitize CSV cell to prevent spreadsheet formula injection attacks."""
    if not val:
        return ""
    val = val.strip()
    # If cell starts with formula characters (=, +, -, @), prepend with a single quote
    if val.startswith(("=", "+", "-", "@")):
        return "'" + val
    return val


def parse_and_validate_csv(file_stream: bytes, max_recipients: int = 1000) -> Dict[str, Any]:
    """
    Safely parse and validate a CSV recipient file.
    Handles UTF-8 and UTF-8-BOM, checks required headers, validates email/name,
    and identifies duplicate entries within the file.
    """
    # 1. Decode stream handling UTF-8 with BOM safely
    try:
        content_str = file_stream.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content_str = file_stream.decode("latin-1")
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to decode CSV file content: {str(e)}",
                "total_rows": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "valid_rows": [],
                "invalid_rows": [],
            }

    # 2. Parse CSV rows
    f = io.StringIO(content_str)
    reader = csv.reader(f)
    
    rows = []
    for row in reader:
        # Ignore completely empty rows
        if any(cell.strip() for cell in row):
            rows.append(row)

    if not rows:
        return {
            "success": False,
            "error": "The uploaded CSV file is empty.",
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "valid_rows": [],
            "invalid_rows": [],
        }

    # 3. Check header row
    header = [col.strip().lower() for col in rows[0]]
    if "name" not in header or "email" not in header:
        return {
            "success": False,
            "error": "Missing required columns in CSV header. The CSV must contain 'name' and 'email' columns.",
            "header_found": rows[0],
            "total_rows": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "valid_rows": [],
            "invalid_rows": [],
        }

    name_idx = header.index("name")
    email_idx = header.index("email")

    data_rows = rows[1:]
    if len(data_rows) > max_recipients:
        return {
            "success": False,
            "error": f"Uploaded CSV contains {len(data_rows)} rows, which exceeds the configured limit of {max_recipients} recipients per job.",
            "total_rows": len(data_rows),
            "valid_count": 0,
            "invalid_count": 0,
            "valid_rows": [],
            "invalid_rows": [],
        }

    valid_rows = []
    invalid_rows = []
    seen_emails = set()

    for row_idx, row in enumerate(data_rows, start=2):
        row_name = row[name_idx].strip() if len(row) > name_idx else ""
        row_email = row[email_idx].strip() if len(row) > email_idx else ""

        errors = []

        if not row_name:
            errors.append("Recipient name is required")

        if not row_email:
            errors.append("Recipient email is required")
        elif not EMAIL_REGEX.match(row_email):
            errors.append(f"Invalid email format: '{row_email}'")
        else:
            lower_email = row_email.lower()
            if lower_email in seen_emails:
                errors.append(f"Duplicate email found in file: '{row_email}'")
            else:
                seen_emails.add(lower_email)

        row_item = {
            "row_number": row_idx,
            "name": sanitize_cell_value(row_name),
            "email": sanitize_cell_value(row_email),
            "errors": errors,
            "is_valid": len(errors) == 0,
        }

        if len(errors) == 0:
            valid_rows.append(row_item)
        else:
            invalid_rows.append(row_item)

    return {
        "success": True,
        "total_rows": len(data_rows),
        "valid_count": len(valid_rows),
        "invalid_count": len(invalid_rows),
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
    }
