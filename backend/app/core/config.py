import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Broker (Angel One SmartAPI)
    ANGELONE_CLIENT_CODE: str = ""
    ANGELONE_PASSWORD: str = ""
    ANGELONE_TOTP_SECRET: str = ""
    ANGELONE_API_KEY: str = ""

    # Database & Redis
    DATABASE_URL: str = "postgresql://kavach:kavach@db:5432/kavach"
    REDIS_URL: str = "redis://redis:6379/0"

    # Risk Config Defaults
    MAX_DAILY_LOSS_PCT: float = 2.0
    MAX_POSITION_CONCENTRATION_PCT: float = 20.0
    MAX_MARGIN_UTILISATION_PCT: float = 70.0
    KELLY_FRACTION_MULTIPLIER: float = 0.3
    ORDER_VELOCITY_LIMIT_PER_10MIN: int = 5
    EXPIRY_DAY_SIZE_DAMPENER: float = 0.5

    # App Config
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    PAPER_MODE: bool = True

    # Load environment variables from a file if it exists, otherwise just from system env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
