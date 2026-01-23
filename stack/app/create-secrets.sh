#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/secrets.env"

echo "========================================"
echo "  Application Secrets Setup"
echo "========================================"
echo ""

if [ ! -f "$SECRETS_FILE" ]; then
    echo "ERROR: Secrets file not found: ${SECRETS_FILE}"
    exit 1
fi

echo "Loading secrets from ${SECRETS_FILE}..."
source "$SECRETS_FILE"

create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2

    if [ -z "$secret_value" ]; then
        echo "   ERROR: ${secret_name}: value is empty"
        return 1
    fi

    if docker secret ls --format '{{.Name}}' | grep -q "^${secret_name}$"; then
        echo "   WARNING: ${secret_name} already exists → skipping"
    else
        echo "$secret_value" | docker secret create "$secret_name" - > /dev/null
        echo "   SUCCESS: ${secret_name} created"
    fi
}

echo ""
echo "Creating Docker secrets..."

# ------------------------------------------
# POSTGRESQL (shared)
# ------------------------------------------
create_or_update_secret "postgres_user" "$POSTGRES_USER"
create_or_update_secret "postgres_password" "$POSTGRES_PASSWORD"
create_or_update_secret "postgres_host" "$POSTGRES_HOST"

# ------------------------------------------
# DATABASE NAMES
# ------------------------------------------
create_or_update_secret "discussion_db_name" "$DISCUSSION_DB_NAME"
create_or_update_secret "challenge_db_name" "$CHALLENGE_DB_NAME"

# ------------------------------------------
# DATABASE SCHEMAS
# ------------------------------------------
create_or_update_secret "discussion_db_schema" "$DISCUSSION_DB_SCHEMA"
create_or_update_secret "challenge_db_schema" "$CHALLENGE_DB_SCHEMA"

# ------------------------------------------
# REDIS
# ------------------------------------------
create_or_update_secret "redis_url" "$REDIS_URL"

# ------------------------------------------
# KEYCLOAK
# ------------------------------------------
create_or_update_secret "keycloak_url" "$KEYCLOAK_URL"
create_or_update_secret "keycloak_realm" "$KEYCLOAK_REALM"
create_or_update_secret "keycloak_audience" "$KEYCLOAK_AUDIENCE"
create_or_update_secret "keycloak_issuer" "$KEYCLOAK_ISSUER"

# ------------------------------------------
# AWS
# ------------------------------------------
create_or_update_secret "discussion_s3_bucket" "$DISCUSSION_S3_BUCKET"
create_or_update_secret "challenge_s3_bucket" "$CHALLENGE_S3_BUCKET"
create_or_update_secret "s3_access_key_id" "$S3_ACCESS_KEY_ID"
create_or_update_secret "s3_secret_access_key" "$S3_SECRET_ACCESS_KEY"
create_or_update_secret "s3_default_region" "$S3_DEFAULT_REGION"

echo ""
echo "All secrets processed successfully!"
echo "========================================"

