import boto3

from .env_config import env_config

# ------------------------------------------------------------------------------
# AWS S3 Configuration
# ------------------------------------------------------------------------------


s3_client = boto3.client(
    "s3",
    aws_access_key_id=env_config.DISCUSSION_AWS_ACCESS_KEY_ID,
    aws_secret_access_key=env_config.DISCUSSION_AWS_SECRET_ACCESS_KEY,
    region_name=env_config.AWS_DEFAULT_REGION,
)
