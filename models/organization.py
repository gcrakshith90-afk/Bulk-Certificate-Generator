from datetime import datetime, timezone
from extensions import db


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    organization_type = db.Column(db.String(50), nullable=False, default="company")
    # company, college, university, training institute, other
    contact_person = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    address = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    jobs = db.relationship("GenerationJob", back_populates="organization", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def total_certificates(self) -> int:
        from models.certificate import Certificate
        from models.generation_job import GenerationJob
        return (
            db.session.query(db.func.count(Certificate.id))
            .join(GenerationJob, Certificate.job_id == GenerationJob.id)
            .filter(GenerationJob.organization_id == self.id)
            .scalar()
            or 0
        )

    @property
    def successful_certificates(self) -> int:
        from models.certificate import Certificate
        from models.generation_job import GenerationJob
        return (
            db.session.query(db.func.count(Certificate.id))
            .join(GenerationJob, Certificate.job_id == GenerationJob.id)
            .filter(GenerationJob.organization_id == self.id, Certificate.status == "Completed")
            .scalar()
            or 0
        )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "organization_type": self.organization_type,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "phone": self.phone,
            "address": self.address,
            "is_active": self.is_active,
            "total_certificates": self.total_certificates,
            "total_jobs": self.jobs.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Organization {self.name} ({self.organization_type})>"
