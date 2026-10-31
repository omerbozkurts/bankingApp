from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

password_hasher = PasswordHash.recommended()  # Argon2id

# Verified when the customer number does not exist, so both paths take the same time
# and response timing does not reveal which customer numbers are real.
DUMMY_HASH = password_hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    return password_hasher.verify(password, password_hash or DUMMY_HASH) and bool(password_hash)


def create_access_token(customer_id: int, session_version: int = 0) -> tuple[str, int]:
    """Returns the signed token and its lifetime in seconds."""
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": str(customer_id),
        "type": "access",
        # Must match the customer's current session_version (see deps.get_current_customer).
        "ver": session_version,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires_in


def decode_access_token(token: str) -> tuple[int, int] | None:
    """Customer id and session version, or None if the token is invalid, expired or not an
    access token. Tokens from before session versions existed count as version 0."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    version = payload.get("ver", 0)
    # bool is an int subclass; a forged `true` must not pass as version 1.
    if not isinstance(version, int) or isinstance(version, bool):
        return None
    try:
        return int(payload["sub"]), version
    except (TypeError, ValueError):
        return None
