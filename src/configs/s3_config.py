import boto3

from .env_config import env_config


# ------------------------------------------------------------------------------
# AWS S3 Configuration
# ------------------------------------------------------------------------------

_s3_kwargs = {
    "service_name": "s3",
    "aws_access_key_id": env_config.S3_ACCESS_KEY_ID,
    "aws_secret_access_key": env_config.S3_SECRET_ACCESS_KEY,
    "region_name": env_config.S3_DEFAULT_REGION,
}

# Only use custom endpoint if provided
if env_config.S3_ENDPOINT_URL:
    _s3_kwargs["endpoint_url"] = env_config.S3_ENDPOINT_URL

s3_client = boto3.client(**_s3_kwargs)