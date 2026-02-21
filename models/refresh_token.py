from datetime import datetime, timezone

from extensions import db


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    device_id = db.Column(db.String(120), nullable=False, index=True)
    device_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_used_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True, index=True)

    user = db.relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        db.Index("ix_refresh_tokens_user_device", "user_id", "device_id"),
    )
