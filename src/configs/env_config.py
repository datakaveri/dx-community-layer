import warnings
import importlib.metadata
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get the current version of the project from the package metadata
try:
    current_version = importlib.metadata.version("TGDex-Monorepo")
except Exception:
    current_version = "0.0.0"

# Configure Pydantic settings
warnings.filterwarnings("ignore", category=DeprecationWarning)


class EnvConfig(BaseSettings):
    PROJECT_NAME: str = "TGDex-Monorepo"
    API_VERSION: str = current_version
    INSTANCE: str
    BASE_URL: str = "http://127.0.0.1:5000"
    DISCUSSION_DATABASE_URL: str
    DISCUSSION_DB_SCHEMA: str
    CHALLENGE_DATABASE_URL: str
    CHALLENGE_DB_SCHEMA: str
    KEYCLOAK_URL: str
    KEYCLOAK_REALM: str
    KEYCLOAK_AUDIENCE: str
    KEYCLOAK_ISSUER: str
    DISCUSSION_S3_BUCKET: str
    CHALLENGE_S3_BUCKET: str
    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    S3_DEFAULT_REGION: str
    REDIS_URL: str
    ALLOWED_ORIGINS: list[str]
    ACTIVATED_SERVICES: list[str]

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )
    S3_ENDPOINT_URL: str | None = None

    REDIS_URL: str
    ACTIVATED_SERVICES: list[str]


env_config = EnvConfig()
