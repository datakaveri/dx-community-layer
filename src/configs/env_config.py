import warnings
import importlib.metadata
from typing import Literal
from pydantic import field_validator, model_validator
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
    # Path prefix this service is mounted under by the reverse proxy when the
    # proxy strips that prefix before forwarding (e.g. "/community" for
    # https://<host>/community). Needed so the docs page requests
    # /<prefix>/openapi.json instead of /openapi.json. Leave empty when the
    # service is served from the root.
    ROOT_PATH: str = ""
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
    # Service endpoint of an S3-compatible store, e.g.
    # https://pocrakkpc.s3.cyfuture.cloud. Leave unset for AWS S3. Must NOT
    # include the bucket -- boto3 adds it per S3_ADDRESSING_STYLE.
    S3_ENDPOINT_URL: str | None = None
    # Base URL used to build browser-facing URLs for public objects. Falls back
    # to S3_ENDPOINT_URL; one of the two must be set. Give it a value of its own
    # only when the browser reaches the store on a different host than this
    # service does (e.g. AWS, where no endpoint is configured at all).
    S3_PUBLIC_BASE_URL: str | None = None
    # virtual -> https://<bucket>.<host>/<key>; path -> https://<host>/<bucket>/<key>
    # Resolved when unset to whatever botocore would pick on its own: path for a
    # custom endpoint, virtual for AWS.
    S3_ADDRESSING_STYLE: Literal["virtual", "path"] | None = None
    # Presigned-URL signing algorithm. Left to botocore when unset, which means
    # legacy SigV2 at us-east-1. SigV2 is deprecated and worth moving off, but
    # only once `s3v4` has been confirmed working against the provider in use.
    S3_SIGNATURE_VERSION: str | None = None
    # Used by the standalone and cluster modes. Not read in sentinel mode, where
    # the master's address is discovered from the sentinels instead.
    REDIS_URL: str | None = None
    REDIS_CLUSTER_ENABLED: bool = False
    # Sentinel mode. REDIS_SENTINEL_NODES is a comma-separated list of sentinel
    # addresses, e.g. "sentinel-0:26379,sentinel-1:26379,sentinel-2:26379".
    REDIS_SENTINEL_ENABLED: bool = False
    REDIS_SENTINEL_NODES: str | None = None
    REDIS_SENTINEL_MASTER_NAME: str = "mymaster"
    # Credentials for the sentinels themselves. Leave unset when the sentinels
    # do not require auth (often the case even when the master does).
    REDIS_SENTINEL_USERNAME: str | None = None
    REDIS_SENTINEL_PASSWORD: str | None = None
    # Credentials and database for the master discovered through the sentinels.
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    ALLOWED_ORIGINS: list[str]
    ACTIVATED_SERVICES: list[str]

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )

    @field_validator("ROOT_PATH", mode="before")
    @classmethod
    def _normalize_root_path(cls, value: str | None) -> str:
        """Accepts the prefix with or without surrounding slashes and returns it
        in the one shape FastAPI expects: leading slash, no trailing slash."""
        if value is None:
            return ""
        value = value.strip().strip("/")
        return f"/{value}" if value else ""

    @field_validator(
        "S3_ENDPOINT_URL",
        "S3_PUBLIC_BASE_URL",
        "S3_ADDRESSING_STYLE",
        "S3_SIGNATURE_VERSION",
        "REDIS_URL",
        "REDIS_SENTINEL_NODES",
        "REDIS_SENTINEL_USERNAME",
        "REDIS_SENTINEL_PASSWORD",
        "REDIS_USERNAME",
        "REDIS_PASSWORD",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        """Treat an empty/whitespace value as unset, so deployments can pass
        the variable through unconditionally (e.g. `${S3_ENDPOINT_URL:-}`)."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def _check_redis_settings(self) -> "EnvConfig":
        """Fails at startup on a Redis configuration that cannot work, rather
        than on the first request that touches the cache."""
        if self.REDIS_CLUSTER_ENABLED and self.REDIS_SENTINEL_ENABLED:
            raise ValueError(
                "REDIS_CLUSTER_ENABLED and REDIS_SENTINEL_ENABLED are mutually "
                "exclusive; enable at most one."
            )

        if self.REDIS_SENTINEL_ENABLED:
            if not self.redis_sentinel_nodes:
                raise ValueError(
                    "REDIS_SENTINEL_ENABLED is set but REDIS_SENTINEL_NODES is "
                    "empty. Set it to e.g. 'sentinel-0:26379,sentinel-1:26379'."
                )
        elif self.REDIS_URL is None:
            raise ValueError(
                "REDIS_URL is required unless REDIS_SENTINEL_ENABLED is set."
            )

        return self

    @property
    def redis_sentinel_nodes(self) -> list[tuple[str, int]]:
        """REDIS_SENTINEL_NODES parsed into the (host, port) pairs redis-py
        expects. A node given without a port gets the sentinel default, 26379."""
        nodes: list[tuple[str, int]] = []
        for node in (self.REDIS_SENTINEL_NODES or "").split(","):
            node = node.strip()
            if not node:
                continue
            host, _, port = node.rpartition(":")
            if not host:
                host, port = port, ""
            try:
                nodes.append((host, int(port) if port else 26379))
            except ValueError:
                raise ValueError(
                    f"Invalid REDIS_SENTINEL_NODES entry {node!r}; "
                    "expected host:port."
                ) from None
        return nodes

    @model_validator(mode="after")
    def _resolve_s3_settings(self) -> "EnvConfig":
        """Pins down the S3 settings once, at startup, so nothing downstream has
        to know how the fallback chains work.

        There is deliberately no built-in default for the public base URL: an
        unconfigured deployment should fail here rather than serve object URLs
        pointing at someone else's object store.
        """
        base_url = self.S3_PUBLIC_BASE_URL or self.S3_ENDPOINT_URL

        if base_url is None:
            raise ValueError(
                "No S3 public base URL configured. Set S3_PUBLIC_BASE_URL "
                "(e.g. https://s3.amazonaws.com for AWS S3), or S3_ENDPOINT_URL "
                "when using an S3-compatible store."
            )

        self.S3_PUBLIC_BASE_URL = base_url.rstrip("/")

        # Mirror botocore's own choice, so leaving this unset changes nothing
        # about how buckets are addressed -- it only makes the choice available
        # to public_object_url(), which has to match it.
        if self.S3_ADDRESSING_STYLE is None:
            self.S3_ADDRESSING_STYLE = "path" if self.S3_ENDPOINT_URL else "virtual"

        return self


env_config = EnvConfig()
