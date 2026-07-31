import boto3
from botocore.config import Config

from .env_config import env_config


# ------------------------------------------------------------------------------
# S3 Configuration (AWS or any S3-compatible provider)
# ------------------------------------------------------------------------------

# The addressing style is passed explicitly because public_object_url() has to
# build unsigned URLs that match how boto3 addresses the bucket; when unset it
# resolves to botocore's own choice, so this is a no-op. The signature version
# is left out entirely unless configured -- passing None is not the same as
# omitting it, and would override botocore's default.
_s3_config_kwargs = {"s3": {"addressing_style": env_config.S3_ADDRESSING_STYLE}}

if env_config.S3_SIGNATURE_VERSION:
    _s3_config_kwargs["signature_version"] = env_config.S3_SIGNATURE_VERSION

_s3_config = Config(**_s3_config_kwargs)

_s3_kwargs = {
    "service_name": "s3",
    "aws_access_key_id": env_config.S3_ACCESS_KEY_ID,
    "aws_secret_access_key": env_config.S3_SECRET_ACCESS_KEY,
    "region_name": env_config.S3_DEFAULT_REGION,
    "config": _s3_config,
}

# Only use custom endpoint if provided
if env_config.S3_ENDPOINT_URL:
    _s3_kwargs["endpoint_url"] = env_config.S3_ENDPOINT_URL

s3_client = boto3.client(**_s3_kwargs)


def public_object_url(bucket: str, object_key: str) -> str:
    """
    Builds the browser-facing URL for a publicly readable object.

    boto3 applies S3_ENDPOINT_URL only to signed API calls, so unsigned URLs
    handed to clients must be composed here. The base URL is resolved once in
    EnvConfig, so this only has to apply the bucket addressing style.
    """
    base_url = env_config.S3_PUBLIC_BASE_URL

    if env_config.S3_ADDRESSING_STYLE == "path":
        return f"{base_url}/{bucket}/{object_key}"

    scheme, _, host = base_url.partition("://")
    return f"{scheme}://{bucket}.{host}/{object_key}"
