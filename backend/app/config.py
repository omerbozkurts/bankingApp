from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # No default on purpose: the app must not start with a guessable signing key.
    jwt_secret: str = Field(min_length=32)
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


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
