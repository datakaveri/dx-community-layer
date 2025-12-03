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
    DISCUSSION_AWS_S3_BUCKET: str
    CHALLENGE_AWS_S3_BUCKET: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_DEFAULT_REGION: str
    REDIS_URL: str
    ACTIVATED_SERVICES: list[str]

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )


env_config = EnvConfig()
