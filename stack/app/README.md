# TGDex Discussion Application Stack

This directory contains the Docker Swarm stack configuration for deploying the TGDex Discussion application.

## Files

- `stack.yml` - Docker Swarm stack configuration
- `entrypoint.sh` - Application entrypoint script
- `create-secrets.sh` - Script to create Docker secrets
- `secrets.env.example` - Template for secrets configuration

## Prerequisites

1. Docker Swarm must be initialized
2. External network `tgdex-network` must exist
3. Docker secrets can be created using the create-secrets.sh (PostgreSQL, Redis, Keycloak, AWS credentials)

## Setup

### 1. Configure Secrets

Copy the example file and fill in your values:

```bash
cp secrets.env.example secrets.env
```

Edit `secrets.env` and provide values for:

- Database schema name
- Keycloak authentication settings (URL, realm, audience, issuer)
- AWS S3 configuration (bucket, access keys, region)

### 2. Create Docker Secrets

Run the secrets creation script:

```bash
./create-secrets.sh
```

This will create Docker secrets from your `secrets.env` file.

### 3. Deploy the Stack

```bash
docker stack deploy -c stack.yml tgdex-app
```

## Configuration

### Environment Variables

- `INSTANCE` - Deployment instance (default: production)
- `BASE_URL` - Base URL for the application (default: http://localhost:5000)

### Secrets

The application uses the following Docker secrets:

- `postgres_db` - PostgreSQL database name
- `postgres_user` - PostgreSQL username
- `postgres_password` - PostgreSQL password
- `db_schema` - Database schema name
- `redis_url` - Redis connection URL
- `keycloak_url` - Keycloak server URL
- `keycloak_realm` - Keycloak realm name
- `keycloak_audience` - Keycloak audience
- `keycloak_issuer` - Keycloak token issuer
- `aws_s3_bucket` - AWS S3 bucket name
- `aws_access_key_id` - AWS access key ID
- `aws_secret_access_key` - AWS secret access key
- `aws_default_region` - AWS default region

### Resources

- CPU Limit: 1 core
- Memory Limit: 1GB
- CPU Reservation: 0.5 core
- Memory Reservation: 512MB

### Health Check

The service health is monitored via HTTP endpoint at `/healthz`. Health checks run every 30 seconds with a 10-second timeout.

## Ports

The application is exposed on port `5000`.

## Management

### View Service Status

```bash
docker service ls
docker service ps tgdex-app_app
```

### View Logs

```bash
docker service logs -f tgdex-app_app
```

### Scale the Service

```bash
docker service scale tgdex-app_app=3
```

### Update the Service

```bash
docker service update --image tgdex-discussion:new-tag tgdex-app_app
```

### Remove the Stack

```bash
docker stack rm tgdex-app
```
