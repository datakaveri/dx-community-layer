This directory contains the Docker Swarm stack configuration for deploying PostgreSQL database for the TGDex Discussion application.

## Files

- `stack.yml` - Docker Swarm stack configuration
- `create-secrets.sh` - Script to create Docker secrets
- `secrets.env.example` - Template for database credentials

## Prerequisites

1. Docker Swarm must be initialized
2. External network `tgdex-network` must exist

## Setup

### 1. Configure Secrets

Copy the example file and fill in your values:

```bash
cp secrets.env.example secrets.env
```

Edit `secrets.env` and provide values for:

- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password (use a strong password)

### 2. Initialization Scripts

Place any `.sql` or `.sh` initialization scripts in the `init-scripts/` directory. These will be executed in alphabetical order when the database is first created.

### 3. Create Docker Secrets

Run the secrets creation script:

```bash
./create-secrets.sh
```

This will create the following Docker secrets:

- `postgres_db`
- `postgres_user`
- `postgres_password`

### 4. Deploy the Stack

```bash
docker stack deploy -c stack.yml tgdex-postgres
```

## Configuration

### Resources

- CPU Limit: 2 cores
- Memory Limit: 2GB
- CPU Reservation: 1 core
- Memory Reservation: 1GB

## Management

### View Service Status

```bash
docker service ls
docker service ps tgdex-postgres_postgres
```

### View Logs

```bash
docker service logs -f tgdex-postgres_postgres
```

### Connect to Database

From within the Docker network:

```bash
docker exec -it $(docker ps -q -f name=tgdex-postgres_postgres) psql -U <username> -d <database>
```

From host machine:

```bash
psql -h localhost -p 5432 -U <username> -d <database>
```

### Remove the Stack

```bash
docker stack rm tgdex-postgres
```

## Initialization Scripts

Scripts placed in `init-scripts/` are executed only on first database creation. Supported formats:

- `.sql` - SQL scripts

## Swarm Deployment with Host-Mode Publishing

To deploy the PostgreSQL stack with host-mode port publishing (binding directly to 0.0.0.0:5432), use both configuration files:

```bash
docker stack deploy -c stack.yml -c custom-expose.yaml db
```

This command uses `custom-expose.yaml` to override the normal port configuration with host-mode publishing, which allows the PostgreSQL service to be accessible from outside the Docker network on port 5432 of the host machine. The `custom-expose.yaml` file configures the service to use host networking mode for the port exposure, making it directly accessible at `0.0.0.0:5432`.
