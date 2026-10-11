from datetime import datetime, timezone
import secrets
import string
from extensions import db


def generate_unique_code(prefix="CERT") -> str:
    """Generate a clean, professional, unique certificate verification code."""
    year = datetime.now(timezone.utc).year
    chars = string.ascii_uppercase + string.digits
    random_str = "".join(secrets.choice(chars) for _ in range(8))
    return f"{prefix}-{year}-{random_str}"


class Certificate(db.Model):
    __tablename__ = "certificates"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("generation_jobs.id"), nullable=False, index=True)
    recipient_name = db.Column(db.String(150), nullable=False, index=True)
    recipient_email = db.Column(db.String(150), nullable=False, index=True)
    certificate_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(30), default="Pending", nullable=False, index=True)
    # 'Pending', 'Processing', 'Completed', 'Failed'
    file_path = db.Column(db.String(300), nullable=True)  # Filename or relative path inside GENERATED_CERTIFICATES_FOLDER
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    generated_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    job = db.relationship("GenerationJob", back_populates="certificates")
    activities = db.relationship("ActivityLog", back_populates="certificate", lazy="dynamic")

    @property
    def organization(self):
        return self.job.organization if self.job else None

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "recipient_name": self.recipient_name,
            "recipient_email": self.recipient_email,
            "certificate_code": self.certificate_code,
            "status": self.status,
            "file_available": bool(self.file_path and self.status == "Completed"),
            "file_path": self.file_path,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "organization_name": self.job.organization.name if (self.job and self.job.organization) else None,
            "course_name": self.job.course_name if self.job else None,
            "issue_date": self.job.issue_date.isoformat() if (self.job and self.job.issue_date) else None,
        }

    def __repr__(self):
        return f"<Certificate {self.certificate_code} ({self.recipient_name} - {self.status})>"
