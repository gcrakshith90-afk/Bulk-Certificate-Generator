from datetime import datetime, timezone
from extensions import db


class GenerationJob(db.Model):
    __tablename__ = "generation_jobs"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False, index=True)
    course_name = db.Column(db.String(200), nullable=False, index=True)
    certificate_title = db.Column(db.String(200), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    completion_date = db.Column(db.Date, nullable=True)
    signatory_name = db.Column(db.String(100), nullable=True)
    signatory_designation = db.Column(db.String(100), nullable=True)
    source_type = db.Column(db.String(20), nullable=False, default="manual")  # 'manual' or 'csv'
    status = db.Column(db.String(30), default="Queued", nullable=False, index=True)
    # 'Queued', 'Processing', 'Completed', 'Completed with failures', 'Failed', 'Cancelled'
    total = db.Column(db.Integer, default=0, nullable=False)
    completed = db.Column(db.Integer, default=0, nullable=False)
    failed = db.Column(db.Integer, default=0, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    organization = db.relationship("Organization", back_populates="jobs")
    creator = db.relationship("User", back_populates="jobs")
    certificates = db.relationship("Certificate", back_populates="job", lazy="dynamic", cascade="all, delete-orphan")
    activities = db.relationship("ActivityLog", back_populates="job", lazy="dynamic")

    @property
    def pending_count(self) -> int:
        pending = self.total - (self.completed + self.failed)
        return max(0, pending)

    @property
    def progress_percentage(self) -> float:
        if not self.total or self.total <= 0:
            return 0.0
        val = ((self.completed + self.failed) / self.total) * 100.0
        return round(min(100.0, val), 1)

    @property
    def success_rate(self) -> float:
        if not self.total or self.total <= 0:
            return 0.0
        val = (self.completed / self.total) * 100.0
        return round(min(100.0, val), 1)

    def update_status_from_counters(self):
        """Update job status consistently based on counters and states."""
        processed = self.completed + self.failed
        if self.status == "Cancelled":
            return
        if processed >= self.total and self.total > 0:
            if self.failed == 0:
                self.status = "Completed"
            elif self.completed == 0:
                self.status = "Failed"
            else:
                self.status = "Completed with failures"
            if not self.completed_at:
                self.completed_at = datetime.now(timezone.utc)
        elif processed > 0 or self.status == "Processing":
            self.status = "Processing"
            if not self.started_at:
                self.started_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "organization_name": self.organization.name if self.organization else None,
            "course_name": self.course_name,
            "certificate_title": self.certificate_title,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "signatory_name": self.signatory_name,
            "signatory_designation": self.signatory_designation,
            "source_type": self.source_type,
            "status": self.status,
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "pending": self.pending_count,
            "progress_percentage": self.progress_percentage,
            "success_rate": self.success_rate,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return f"<GenerationJob #{self.id} {self.course_name} ({self.status})>"
