from datetime import datetime, timezone, date
from typing import List, Dict, Any, Tuple
from extensions import db
from models.organization import Organization
from models.generation_job import GenerationJob
from models.certificate import Certificate, generate_unique_code
from models.activity_log import ActivityLog
from tasks.certificate_tasks import enqueue_generation_job


def resolve_organization(
    organization_id: int | None = None,
    new_org_name: str | None = None,
    new_org_type: str = "company",
    contact_person: str = "Administrator",
    contact_email: str = "admin@organization.local",
) -> Tuple[Organization | None, str | None]:
    """Resolve an existing organization by ID or safely create a new one without duplicates."""
    if organization_id:
        org = db.session.get(Organization, organization_id)
        if org:
            if not org.is_active:
                return None, f"Organization '{org.name}' is inactive and cannot generate certificates."
            return org, None
        return None, f"Organization with ID {organization_id} was not found."

    if new_org_name and new_org_name.strip():
        clean_name = new_org_name.strip()
        existing = Organization.query.filter(db.func.lower(Organization.name) == clean_name.lower()).first()
        if existing:
            if not existing.is_active:
                return None, f"Organization '{existing.name}' exists but is inactive."
            return existing, None

        org = Organization(
            name=clean_name,
            organization_type=new_org_type or "company",
            contact_person=contact_person or "Administrator",
            contact_email=contact_email or "contact@organization.local",
            is_active=True,
        )
        db.session.add(org)
        db.session.flush()

        log = ActivityLog(
            event_type="ORGANIZATION_CREATED",
            description=f"Auto-created organization '{org.name}' during certificate generation.",
        )
        db.session.add(log)
        return org, None

    return None, "Please select an existing organization or provide a new organization name."


def create_bulk_generation_job(
    organization: Organization,
    course_name: str,
    certificate_title: str,
    issue_date: date,
    recipients: List[Dict[str, str]],
    source_type: str = "manual",
    completion_date: date | None = None,
    signatory_name: str | None = None,
    signatory_designation: str | None = None,
    created_by: int | None = None,
    max_recipients: int = 1000,
) -> Tuple[GenerationJob | None, str | None]:
    """
    Validate recipients, create GenerationJob and Certificate records atomically,
    and dispatch generation to background worker.
    """
    if not recipients or len(recipients) == 0:
        return None, "Recipient list cannot be empty."

    if len(recipients) > max_recipients:
        return None, f"Recipient list exceeds maximum allowed limit of {max_recipients} recipients."

    # Validate individual recipients
    valid_recipients = []
    for idx, r in enumerate(recipients, start=1):
        name = r.get("name", "").strip()
        email = r.get("email", "").strip()
        if not name or not email:
            return None, f"Recipient #{idx} is missing name or email address."
        valid_recipients.append({"name": name, "email": email})

    try:
        # Create Job
        job = GenerationJob(
            organization_id=organization.id,
            course_name=course_name.strip(),
            certificate_title=certificate_title.strip(),
            issue_date=issue_date,
            completion_date=completion_date,
            signatory_name=signatory_name.strip() if signatory_name else None,
            signatory_designation=signatory_designation.strip() if signatory_designation else None,
            source_type=source_type,
            status="Queued",
            total=len(valid_recipients),
            completed=0,
            failed=0,
            created_by=created_by,
        )
        db.session.add(job)
        db.session.flush()

        # Batch insert Certificate records
        for r in valid_recipients:
            cert = Certificate(
                job_id=job.id,
                recipient_name=r["name"],
                recipient_email=r["email"].lower(),
                certificate_code=generate_unique_code(),
                status="Pending",
            )
            db.session.add(cert)

        # Log Activity
        log = ActivityLog(
            user_id=created_by,
            job_id=job.id,
            event_type="JOB_CREATED",
            description=f"Created Job #{job.id} for '{job.course_name}' with {len(valid_recipients)} recipients ({source_type}).",
        )
        db.session.add(log)

        db.session.commit()

        # Queue background processing
        enqueue_generation_job(job.id)

        return job, None

    except Exception as e:
        db.session.rollback()
        return None, f"Failed to initialize certificate generation job: {str(e)}"
