#!/bin/bash
set -e

# PostgreSQL Secrets Creation Script
# ===================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="${SCRIPT_DIR}/secrets.env"

echo "========================================"
echo "  PostgreSQL Secrets Setup"
echo "========================================"
echo ""

# Check if secrets file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "ERROR: Secrets file not found: ${SECRETS_FILE}"
    echo "Please create it from the example:"
    echo "   cp ${SCRIPT_DIR}/secrets.env.example ${SECRETS_FILE}"
    exit 1
fi

# Load secrets
echo "Loading secrets from ${SECRETS_FILE}..."
source "$SECRETS_FILE"

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2

    if [ -z "$secret_value" ]; then
        echo "   ERROR: ${secret_name}: value is empty"
        return 1
    fi

    # Check if secret exists
    if docker secret ls --format '{{.Name}}' | grep -q "^${secret_name}$"; then
        echo "   WARNING: ${secret_name}: already exists (skipping)"
    else
        echo "$secret_value" | docker secret create "$secret_name" - > /dev/null
        echo "   SUCCESS: ${secret_name}: created"
    fi
}

# Create secrets
echo "Creating PostgreSQL secrets..."
create_or_update_secret "postgres_db" "$POSTGRES_DB"
create_or_update_secret "postgres_user" "$POSTGRES_USER"
create_or_update_secret "postgres_password" "$POSTGRES_PASSWORD"

echo ""
echo "PostgreSQL secrets created successfully!"
echo ""
