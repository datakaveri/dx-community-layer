#!/bin/sh
set -e

echo "Starting TGDex application..."

echo "Reading secrets from /run/secrets/..."

# PostgreSQL Configuration (shared)
if [ -f /run/secrets/postgres_user ]; then
  export POSTGRES_USER=$(cat /run/secrets/postgres_user)
  echo "POSTGRES_USER loaded"
else
  echo "ERROR: postgres_user secret not found"
  exit 1
fi

if [ -f /run/secrets/postgres_password ]; then
  export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
  echo "POSTGRES_PASSWORD loaded"
else
  echo "ERROR: postgres_password secret not found"
  exit 1
fi

if [ -f /run/secrets/postgres_host ]; then
  export POSTGRES_HOST=$(cat /run/secrets/postgres_host)
  echo "POSTGRES_HOST loaded"
else
  echo "ERROR: postgres_host secret not found"
  exit 1
fi

# Discussion Database
if [ -f /run/secrets/discussion_db_name ]; then
  export DISCUSSION_DB_NAME=$(cat /run/secrets/discussion_db_name)
  echo "DISCUSSION_DB_NAME loaded"
else
  echo "ERROR: discussion_db_name secret not found"
  exit 1
fi

# Challenge Database
if [ -f /run/secrets/challenge_db_name ]; then
  export CHALLENGE_DB_NAME=$(cat /run/secrets/challenge_db_name)
  echo "CHALLENGE_DB_NAME loaded"
else
  echo "ERROR: challenge_db_name secret not found"
  exit 1
fi

# Construct DATABASE URLs
export DISCUSSION_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${DISCUSSION_DB_NAME}"
export CHALLENGE_DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${CHALLENGE_DB_NAME}"
echo "DISCUSSION_DATABASE_URL constructed"
echo "CHALLENGE_DATABASE_URL constructed"

# Redis
if [ -f /run/secrets/redis_url ]; then
  export REDIS_URL=$(cat /run/secrets/redis_url)
  echo "REDIS_URL loaded"
else
  echo "ERROR: redis_url secret not found"
  exit 1
fi

# DB Schemas
if [ -f /run/secrets/discussion_db_schema ]; then
  export DISCUSSION_DB_SCHEMA=$(cat /run/secrets/discussion_db_schema)
  echo "DISCUSSION_DB_SCHEMA loaded"
else
  echo "ERROR: discussion_db_schema secret not found"
  exit 1
fi

if [ -f /run/secrets/challenge_db_schema ]; then
  export CHALLENGE_DB_SCHEMA=$(cat /run/secrets/challenge_db_schema)
  echo "CHALLENGE_DB_SCHEMA loaded"
else
  echo "ERROR: challenge_db_schema secret not found"
  exit 1
fi

# Keycloak
if [ -f /run/secrets/keycloak_url ]; then
  export KEYCLOAK_URL=$(cat /run/secrets/keycloak_url)
  echo "KEYCLOAK_URL loaded"
else
  echo "ERROR: keycloak_url secret not found"
  exit 1
fi

if [ -f /run/secrets/keycloak_realm ]; then
  export KEYCLOAK_REALM=$(cat /run/secrets/keycloak_realm)
  echo "KEYCLOAK_REALM loaded"
else
  echo "ERROR: keycloak_realm secret not found"
  exit 1
fi

if [ -f /run/secrets/keycloak_audience ]; then
  export KEYCLOAK_AUDIENCE=$(cat /run/secrets/keycloak_audience)
  echo "KEYCLOAK_AUDIENCE loaded"
else
  echo "ERROR: keycloak_audience secret not found"
  exit 1
fi

if [ -f /run/secrets/keycloak_issuer ]; then
  export KEYCLOAK_ISSUER=$(cat /run/secrets/keycloak_issuer)
  echo "KEYCLOAK_ISSUER loaded"
else
  echo "ERROR: keycloak_issuer secret not found"
  exit 1
fi

# AWS S3 Buckets
if [ -f /run/secrets/discussion_aws_s3_bucket ]; then
  export DISCUSSION_AWS_S3_BUCKET=$(cat /run/secrets/discussion_aws_s3_bucket)
  echo "DISCUSSION_AWS_S3_BUCKET loaded"
else
  echo "ERROR: discussion_aws_s3_bucket secret not found"
  exit 1
fi

if [ -f /run/secrets/challenge_aws_s3_bucket ]; then
  export CHALLENGE_AWS_S3_BUCKET=$(cat /run/secrets/challenge_aws_s3_bucket)
  echo "CHALLENGE_AWS_S3_BUCKET loaded"
else
  echo "ERROR: challenge_aws_s3_bucket secret not found"
  exit 1
fi

if [ -f /run/secrets/aws_access_key_id ]; then
  export AWS_ACCESS_KEY_ID=$(cat /run/secrets/aws_access_key_id)
  echo "AWS_ACCESS_KEY_ID loaded"
else
  echo "ERROR: aws_access_key_id secret not found"
  exit 1
fi

if [ -f /run/secrets/aws_secret_access_key ]; then
  export AWS_SECRET_ACCESS_KEY=$(cat /run/secrets/aws_secret_access_key)
  echo "AWS_SECRET_ACCESS_KEY loaded"
else
  echo "ERROR: aws_secret_access_key secret not found"
  exit 1
fi

if [ -f /run/secrets/aws_default_region ]; then
  export AWS_DEFAULT_REGION=$(cat /run/secrets/aws_default_region)
  echo "AWS_DEFAULT_REGION loaded"
else
  echo "ERROR: aws_default_region secret not found"
  exit 1
fi

echo ""
echo "All secrets loaded successfully!"
echo ""
echo "Configuration:"
echo "   - Instance: ${INSTANCE}"
echo "   - Base URL: ${BASE_URL}"
echo "   - Discussion DB: ${DISCUSSION_DB_NAME}"
echo "   - Challenge DB: ${CHALLENGE_DB_NAME}"
echo "   - Discussion Schema: ${DISCUSSION_DB_SCHEMA}"
echo "   - Challenge Schema: ${CHALLENGE_DB_SCHEMA}"
echo "   - AWS Region: ${AWS_DEFAULT_REGION}"
echo ""

echo "Waiting for PostgreSQL to be ready..."
until nc -z "${POSTGRES_HOST}" 5432 2>/dev/null; do
  echo "   PostgreSQL unavailable - sleeping"
  sleep 2
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis to be ready..."
# Extract Redis host from REDIS_URL (format: redis://user:pass@host:port)
REDIS_HOST=$(echo "$REDIS_URL" | sed -e 's|redis://||' -e 's|.*@||' -e 's|:.*||')
until nc -z "${REDIS_HOST}" 6379 2>/dev/null; do
  echo "   Redis unavailable - sleeping"
  sleep 2
done
echo "Redis is ready!"

echo ""
echo "Starting FastAPI server..."
echo ""

exec server
