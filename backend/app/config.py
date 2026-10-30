from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # No default on purpose: the app must not start with a guessable signing key.
    jwt_secret: str = Field(min_length=32)
    # Key for hashing T.C. identity numbers. Changing it orphans existing digests: keep it stable.
    national_id_pepper: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:8081"]

    # Web clients keep the session in an httpOnly cookie instead of JS-readable storage.
    session_cookie_name: str = "abbank_session"
    # Browsers accept Secure cookies on http://localhost, so this can stay on in development.
    session_cookie_secure: bool = True

    # Lock an account for a while after repeated wrong passwords.
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # Per-IP cap on login attempts, independent of which customer number is tried.
    login_rate_limit: int = 20
    login_rate_window_seconds: int = 300
    register_rate_limit: int = 5
    register_rate_window_seconds: int = 3600
    # Recipient lookups per customer, so IBANs can't be scanned to harvest masked names.
    lookup_rate_limit: int = 30
    lookup_rate_window_seconds: int = 300

    # Transfer limits in kuruş: 50.000 TL per transfer, 100.000 TL per customer per rolling 24 h.
    transfer_max_kurus: int = 5_000_000
    transfer_daily_max_kurus: int = 10_000_000

    # Interest-free revolving credit: every customer can open one credit account with this limit.
    credit_limit_kurus: int = 2_000_000  # 20.000 TL


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
