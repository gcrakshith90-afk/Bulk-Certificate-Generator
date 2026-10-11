from datetime import datetime, timezone
from extensions import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("generation_jobs.id"), nullable=True, index=True)
    certificate_id = db.Column(db.Integer, db.ForeignKey("certificates.id"), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="activities")
    job = db.relationship("GenerationJob", back_populates="activities")
    certificate = db.relationship("Certificate", back_populates="activities")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else "System",
            "job_id": self.job_id,
            "certificate_id": self.certificate_id,
            "event_type": self.event_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ActivityLog {self.event_type} - {self.description[:30]}>"
