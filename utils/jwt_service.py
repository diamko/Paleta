import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

from extensions import db
from models.refresh_token import RefreshToken
from models.user import User


class AuthError(Exception):
    def __init__(self, code: str, message: str, status: int = 401):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_naive() -> datetime:
    return _utcnow().replace(tzinfo=None)


def _secret() -> str:
    return current_app.config["JWT_SECRET_KEY"]


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _issue_access_token(user_id: int) -> tuple[str, int]:
    now = _utcnow()
    ttl_minutes = max(1, int(current_app.config["JWT_ACCESS_TTL_MINUTES"]))
    expires_at = now + timedelta(minutes=ttl_minutes)

    payload = {
        "sub": str(user_id),
        "iss": current_app.config["JWT_ISSUER"],
        "aud": current_app.config["JWT_AUDIENCE"],
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, _secret(), algorithm="HS256")
    return token, ttl_minutes * 60


def _issue_refresh_token(user_id: int, device_id: str, device_name: str | None):
    now = _utcnow()
    ttl_days = max(1, int(current_app.config["JWT_REFRESH_TTL_DAYS"]))
    expires_at = now + timedelta(days=ttl_days)
    raw_token = secrets.token_urlsafe(48)
    refresh = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw_token),
        device_id=device_id,
        device_name=(device_name or "").strip() or None,
        expires_at=expires_at.replace(tzinfo=None),
        last_used_at=now.replace(tzinfo=None),
    )
    db.session.add(refresh)
    return raw_token


def issue_token_pair(user_id: int, device_id: str, device_name: str | None):
    access_token, expires_in = _issue_access_token(user_id)
    refresh_token = _issue_refresh_token(user_id, device_id, device_name)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": "Bearer",
    }


def parse_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=["HS256"],
            audience=current_app.config["JWT_AUDIENCE"],
            issuer=current_app.config["JWT_ISSUER"],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("AUTH_TOKEN_EXPIRED", "Токен доступа истек", 401) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("AUTH_INVALID_TOKEN", "Недействительный токен доступа", 401) from exc

    if payload.get("type") != "access":
        raise AuthError("AUTH_INVALID_TOKEN", "Некорректный тип токена", 401)
    return payload


def get_user_from_access_token(token: str) -> User:
    payload = parse_access_token(token)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise AuthError("AUTH_INVALID_TOKEN", "Некорректный токен доступа", 401) from exc

    user = db.session.get(User, user_id)
    if not user:
        raise AuthError("AUTH_INVALID_TOKEN", "Пользователь токена не найден", 401)
    return user


def get_active_refresh_token(raw_token: str) -> RefreshToken:
    token_hash = _hash_token(raw_token)
    token = RefreshToken.query.filter_by(token_hash=token_hash).first()
    if not token:
        raise AuthError("AUTH_INVALID_REFRESH", "Недействительный refresh token", 401)

    now = _utcnow_naive()
    if token.revoked_at is not None:
        raise AuthError("AUTH_INVALID_REFRESH", "Refresh token отозван", 401)
    if token.expires_at <= now:
        raise AuthError("AUTH_REFRESH_EXPIRED", "Refresh token истек", 401)
    return token


def rotate_refresh_token(raw_refresh_token: str, device_id: str, device_name: str | None):
    token = get_active_refresh_token(raw_refresh_token)
    now = _utcnow_naive()
    token.revoked_at = now
    token.last_used_at = now
    return token.user_id, issue_token_pair(token.user_id, device_id=device_id, device_name=device_name)


def revoke_refresh_token(raw_refresh_token: str) -> bool:
    token_hash = _hash_token(raw_refresh_token)
    token = RefreshToken.query.filter_by(token_hash=token_hash).first()
    if not token:
        return False

    if token.revoked_at is None:
        now = _utcnow_naive()
        token.revoked_at = now
        token.last_used_at = now
    return True
