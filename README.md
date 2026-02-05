# TGDex-MonoRepo

TGDex-MonoRepo is a **FastAPI** application that provides all **TGDex** microservices: **Discussion** and **Challenge** APIs. You can enable one or both via configuration.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Deployments](#deployments)
  - [Docker (standalone)](#1-docker-standalone)
  - [GitHub Actions (CI/CD)](#2-github-actions-cicd)
  - [Docker Swarm (stack)](#3-docker-swarm-stack)
  - [Kubernetes](#4-kubernetes)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Authors](#authors)

---

## Requirements

| Requirement    | Version / Notes                                      |
|----------------|------------------------------------------------------|
| **Python**     | **≥ 3.13** (recommended: **3.13.3**, see `.python-version`) |
| **Poetry**     | **2.x** (recommended: **2.1.4**) for dependency management |
| **poetry-core**| `>=2.0.0,<3.0.0` (build backend in `pyproject.toml`)  |

> **Note:** The **Docker** image uses **Python 3.14.x** (see `Dockerfile`). Local development follows `.python-version` (3.13.3).

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sirpi-in/tgdex-monorepo.git
cd tgdex-monorepo
```

### 2. Install Poetry

If Poetry is not installed:

```bash
pip install poetry==2.1.4
```

Other options: [Poetry installation](https://python-poetry.org/docs/#installation).

### 3. Install dependencies

```bash
poetry install
```

---

## Environment Variables

The app is configured via `pydantic-settings` from `.env` or environment. All of the following are **required** unless otherwise noted.

### Core

| Variable             | Required | Description                                                                 |
|----------------------|----------|-----------------------------------------------------------------------------|
| `INSTANCE`           | Yes      | Environment name (e.g. `development`, `staging`, `production`).             |
| `BASE_URL`           | No       | Base URL of the API (default: `http://127.0.0.1:5000`).                     |
| `ALLOWED_ORIGINS`    | Yes      | JSON array of allowed CORS origins (e.g. `["http://localhost:3000"]`).      |
| `ACTIVATED_SERVICES` | Yes      | JSON array of enabled services: `["DISCUSSION"]`, `["CHALLENGE"]`, or `["DISCUSSION", "CHALLENGE"]`. |

### Databases (PostgreSQL)

| Variable                 | Required | Description                                                                 |
|--------------------------|----------|-----------------------------------------------------------------------------|
| `DISCUSSION_DATABASE_URL`| Yes      | Full URL: `postgresql://USER:PASSWORD@HOST:5432/DATABASE` (Discussion DB).  |
| `DISCUSSION_DB_SCHEMA`   | Yes      | PostgreSQL schema name for Discussion.                                     |
| `CHALLENGE_DATABASE_URL` | Yes      | Full URL: `postgresql://USER:PASSWORD@HOST:5432/DATABASE` (Challenge DB).   |
| `CHALLENGE_DB_SCHEMA`    | Yes      | PostgreSQL schema name for Challenge.                                      |

### Keycloak

| Variable           | Required | Description                    |
|--------------------|----------|--------------------------------|
| `KEYCLOAK_URL`     | Yes      | Keycloak base URL.             |
| `KEYCLOAK_REALM`   | Yes      | Keycloak realm.                |
| `KEYCLOAK_AUDIENCE`| Yes      | Keycloak audience.             |
| `KEYCLOAK_ISSUER`  | Yes      | Keycloak token issuer.         |

### AWS S3

| Variable                    | Required | Description                        |
|-----------------------------|----------|--------------------------------------------------------------------|
| `DISCUSSION_S3_BUCKET`  | Yes      | S3 bucket for Discussion assets.   |
| `CHALLENGE_S3_BUCKET`   | Yes      | S3 bucket for Challenge assets.    |
| `S3_ACCESS_KEY_ID`         | Yes      | AWS access key.                    |
| `S3_SECRET_ACCESS_KEY`     | Yes      | AWS secret key.                    |
| `S3_DEFAULT_REGION`        | Yes      | AWS region (e.g. `us-east-1`).     |
| `S3_ENDPOINT_URL`          | No       | Custom S3 endpoint (e.g. for MinIO).|

### Redis

| Variable    | Required | Description                                                |
|-------------|----------|------------------------------------------------------------|
| `REDIS_URL` | Yes      | Redis URL (e.g. `redis://user:password@host:6379/0`).      |

### Example `.env` (minimal for local)

```env
INSTANCE=development
BASE_URL=http://127.0.0.1:5000
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
ACTIVATED_SERVICES=["DISCUSSION", "CHALLENGE"]

DISCUSSION_DATABASE_URL=postgresql://user:pass@localhost:5432/discussion_db
DISCUSSION_DB_SCHEMA=discussion
CHALLENGE_DATABASE_URL=postgresql://user:pass@localhost:5432/challenge_db
CHALLENGE_DB_SCHEMA=challenge

KEYCLOAK_URL=https://your-keycloak.example.com
KEYCLOAK_REALM=your-realm
KEYCLOAK_AUDIENCE=your-audience
KEYCLOAK_ISSUER=https://your-keycloak.example.com/realms/your-realm

DISCUSSION_S3_BUCKET=your-discussion-bucket
CHALLENGE_S3_BUCKET=your-challenge-bucket
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_DEFAULT_REGION=us-east-1
S3_ENDPOINT_URL= # Optional: your-custom-endpoint (e.g. for MinIO)

REDIS_URL=redis://localhost:6379/0
```

---

## Running Locally

- **Development (hot-reload):**

  ```bash
  poetry run local
  ```

- **Production-like (no reload):**

  ```bash
  poetry run server
  ```

The API listens on **port 5000**. Ensure PostgreSQL, Redis, and (if used) Keycloak and S3 are reachable and variables are set (e.g. via `.env` in the project root).

---

## Deployments

### 1. Docker (standalone)

**Build:**

```bash
docker build -t tgdex-monorepo:latest .
```

**Run:**

```bash
docker run -d \
  --name tgdex-monorepo \
  -p 5000:5000 \
  --env-file .env \
  --restart unless-stopped \
  tgdex-monorepo:latest
```

Use a `.env` with all [environment variables](#environment-variables) (including `DISCUSSION_DATABASE_URL`, `CHALLENGE_DATABASE_URL`, etc.).

---

### 2. GitHub Actions (CI/CD)

The workflow **Deploy TGDex-monorepo-microservices** (`.github/workflows/deploy.yml`) runs on:

- Push to `dev`
- Manual `workflow_dispatch`

**Steps it performs:**

1. Checkout, install Vault CLI.
2. **Fetch secrets** from HashiCorp Vault:  
   `vault kv get -field=monorepo-microservices-dev kv/projects/tgdex` → `.env.production`
3. **Build and push** Docker image to Docker Hub (e.g. `sirpi/tgdex-monorepo-microservices:dev`).
4. **Copy** `.env.production` to the server (e.g. `/tmp/tgdex-monorepo-microservices/`).
5. **Deploy on server:**
   - Move env to `/root/tgdex-monorepo-microservices/.env`
   - Docker login, pull image, stop/rm old container.
   - Start new container with `--env-file` and `-p 8091:5000`, `--restart always`.

**Required GitHub Secrets:**

| Secret            | Description                                |
|-------------------|--------------------------------------------|
| `VAULT_URL`       | Vault address.                             |
| `VAULT_TOKEN`     | Token to read `kv/projects/tgdex`.         |
| `DOCKER_USERNAME` | Docker Hub username.                       |
| `DOCKER_PASSWORD` | Docker Hub password/token.                 |
| `DOCKER_IMAGE_NAME` | Image name (e.g. `sirpi/tgdex-monorepo-microservices`). |
| `CONTAINER_NAME`  | Container name on the server.              |
| `SERVER_HOST`     | Deploy target host.                        |
| `SERVER_USER`     | SSH user.                                  |
| `SSH_PRIVATE_KEY` | SSH private key for deployment.            |

The Vault key `monorepo-microservices-dev` must contain the same variables as the [environment variables](#environment-variables) section (as a blob or key-value that can be written into `.env.production`).

---

### 3. Docker Swarm (stack)

The **app** stack (`stack/app/`) expects Docker **secrets** and uses `entrypoint.sh` to build `DISCUSSION_DATABASE_URL` and `CHALLENGE_DATABASE_URL` from separate DB secrets. The **postgres** and **redis** stacks are separate.

#### Prerequisites

- Docker Swarm initialized.
- External network: `tgdex-network`.
- PostgreSQL and Redis running and reachable (e.g. via `stack/postgres` and `stack/redis` or your own).

#### 3.1 PostgreSQL stack (if using `stack/postgres`)

```bash
cd stack/postgres
cp secrets.env.example secrets.env
# Edit secrets.env: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
./create-secrets.sh
docker stack deploy -c stack.yml tgdex-postgres
# Optional: host-mode port 5432: add -c custom-expose.yaml to the deploy command
```

Init scripts in `init-scripts/` (e.g. `00_discussion_schema.sql`, `01_challenge_schema.sql`) run on first DB creation.

#### 3.2 Redis (if using `stack/redis`)

```bash
cd stack/redis
docker compose up -d
# Or integrate into your Swarm/network as needed.
```

#### 3.3 App stack

1. **Secrets (from `stack/app/secrets.env`):**

   ```bash
   cd stack/app
   cp secrets.env.example secrets.env
   ```

   Fill `secrets.env` with:

    - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
    - `DISCUSSION_DB_NAME`, `CHALLENGE_DB_NAME`
    - `DISCUSSION_DB_SCHEMA`, `CHALLENGE_DB_SCHEMA`
    - `REDIS_URL`
    - `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_AUDIENCE`, `KEYCLOAK_ISSUER`
    - `DISCUSSION_S3_BUCKET`, `CHALLENGE_S3_BUCKET`
    - `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_DEFAULT_REGION`
    - `ALLOWED_ORIGINS`
    - `S3_ENDPOINT_URL` (Optional)

2. **Create Docker secrets:**

   ```bash
   ./create-secrets.sh
   ```

3. **Set image in `stack.yml`:**

   Replace `<place-holder>` under `services.app.image` with your image (e.g. `tgdex-monorepo:latest` or your registry path).

4. **Deploy:**

   ```bash
   docker stack deploy -c stack.yml tgdex-app
   ```

The app is exposed on **5000** and uses `/healthz` for healthchecks. `INSTANCE`, `BASE_URL`, and `ACTIVATED_SERVICES` are set in `stack.yml`; DB URLs are built by `entrypoint.sh` from the secrets above.

---

### 4. Kubernetes

Manifests are under `k8s-manifests/app/`.

#### deploy.yaml

- Replace `<placeholder>` for `imagePullSecrets.name` if you use a private registry.
- Replace `<placeholder>` for `containers[0].image` with your image (e.g. `sirpi/tgdex-monorepo-microservices:dev`).
- Replace `<placeholder>` for `envFrom.secretRef.name` with the name of a **Secret** that contains the same [environment variables](#environment-variables) as key-value pairs.

**Kubernetes Secret example (literal values; prefer sealed-secrets or external secret operators in production):**

```bash
kubectl create secret generic tgdex-monorepo-secrets --from-literal=INSTANCE=production \
  --from-literal=BASE_URL=https://api.example.com \
  --from-literal=ACTIVATED_SERVICES='["DISCUSSION","CHALLENGE"]' \
  --from-literal=DISCUSSION_DATABASE_URL='postgresql://...' \
  --from-literal=DISCUSSION_DB_SCHEMA=discussion \
  --from-literal=CHALLENGE_DATABASE_URL='postgresql://...' \
  --from-literal=CHALLENGE_DB_SCHEMA=challenge \
  # ... add KEYCLOAK_*, AWS_*, REDIS_URL, etc.
```

Then set `envFrom.secretRef.name` to `tgdex-monorepo-secrets`.

#### service.yaml

- `tgdex-monolith-svc` exposes the app on port **80** (targeting container port **5000**). Adjust if your Ingress or network policy expects a different port.

**Apply:**

```bash
kubectl apply -f k8s-manifests/app/deploy.yaml
kubectl apply -f k8s-manifests/app/service.yaml
```

---

## Project Structure

```
tgdex-monorepo/
├── .github/workflows/
│   └── deploy.yml          # CI/CD for dev branch
├── k8s-manifests/app/      # Kubernetes Deployment and Service
├── stack/
│   ├── app/                # Docker Swarm app stack, entrypoint, create-secrets
│   ├── postgres/           # PostgreSQL stack and init scripts
│   └── redis/              # Redis Compose config
├── src/
│   ├── configs/            # DB, env, Redis, S3 config
│   ├── database/           # Discussion and Challenge models
│   ├── middlewares/        # Auth, logging, search validation
│   ├── routes/             # Challenge, Discussion, utility (incl. /healthz)
│   ├── schemas/            # Pydantic and API schemas
│   ├── services/           # Business logic
│   ├── main.py
│   ├── run.py              # `server` and `local` entrypoints
│   └── docs.py
├── Dockerfile
├── pyproject.toml
├── poetry.lock
├── .python-version
└── README.md
```

---

## API Documentation

- **Swagger UI:** `http://<host>:5000/docs`
- **ReDoc:** `http://<host>:5000/redoc`
- **Health:** `GET /healthz` (used by Docker/Kubernetes healthchecks)

---

## Authors

- **Muzaffar Shaikh** — [muzaffar@sirpi.io](mailto:muzaffar@sirpi.io)
