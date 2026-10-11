import os
import zipfile
import re
import time
from pathlib import Path
from typing import Tuple, Optional
from extensions import db
from models.generation_job import GenerationJob
from models.certificate import Certificate

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated_certificates"
TEMP_ZIP_DIR = BASE_DIR / "temp_zips"

os.makedirs(TEMP_ZIP_DIR, exist_ok=True)


def cleanup_old_zips(max_age_seconds: int = 3600):
    """Clean up temporary zip files older than max_age_seconds (1 hour default)."""
    try:
        now = time.time()
        for f in os.listdir(TEMP_ZIP_DIR):
            f_path = TEMP_ZIP_DIR / f
            if f_path.is_file() and f.endswith(".zip"):
                if now - f_path.stat().st_mtime > max_age_seconds:
                    try:
                        f_path.unlink()
                    except Exception:
                        pass
    except Exception:
        pass


def sanitize_archive_filename(name: str) -> str:
    """Ensure safe filenames inside ZIP archive."""
    clean = re.sub(r"[^a-zA-Z0-9_\-.]", "_", name)
    return clean[:50]


def create_job_certificates_zip(job_id: int) -> Tuple[Optional[Path], Optional[str], int]:
    """
    Create a clean, secure ZIP archive of all successfully generated PDFs for a job.
    Returns: (zip_path, error_message, count_included)
    """
    cleanup_old_zips()

    job = db.session.get(GenerationJob, job_id)
    if not job:
        return None, "Generation job not found.", 0

    successful_certs = Certificate.query.filter_by(job_id=job.id, status="Completed").all()
    if not successful_certs:
        return None, "No completed certificates available to download for this job.", 0

    zip_filename = f"Certificates_Job_{job.id}_{int(time.time())}.zip"
    zip_path = TEMP_ZIP_DIR / zip_filename

    count_included = 0
    try:
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cert in successful_certs:
                if not cert.file_path:
                    continue

                # Ensure strict path containment inside GENERATED_DIR (prevent path traversal)
                source_pdf = (GENERATED_DIR / os.path.basename(cert.file_path)).resolve()
                if not str(source_pdf).startswith(str(GENERATED_DIR.resolve())):
                    continue

                if source_pdf.exists() and source_pdf.is_file():
                    safe_rec_name = sanitize_archive_filename(cert.recipient_name)
                    archive_name = f"{cert.certificate_code}_{safe_rec_name}.pdf"
                    zip_file.write(str(source_pdf), arcname=archive_name)
                    count_included += 1

        if count_included == 0:
            if zip_path.exists():
                zip_path.unlink()
            return None, "No valid certificate PDF files could be found on disk.", 0

        return zip_path, None, count_included

    except Exception as e:
        if zip_path.exists():
            zip_path.unlink()
        return None, f"Failed to generate ZIP archive: {str(e)}", 0
