# DX-Community Layer

DX-Community layer is a **FastAPI** application that provides all **community** microservices: **Discussion** and **Challenge** APIs. You can enable one or both via configuration.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Cron](#cron)
- [Deployments](#deployments)
  - [Docker (standalone)](#1-docker-standalone)
  - [Jenkins (CI/CD)](#2-jenkins-cicd)
  - [Docker Swarm (stack)](#3-docker-swarm-stack)
  - [Kubernetes](#4-kubernetes)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
  - [Running behind a reverse proxy subpath](#running-behind-a-reverse-proxy-subpath)
- [License](#license)

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
git clone https://github.com/datakaveri/dx-community-layer.git
cd dx-community-layer
```

### 2. Install Python and Poetry

Use Python **3.13** or newer (`.python-version` pins **3.13.3**; with pyenv, `pyenv install` inside the repo picks it up).

If Poetry is not installed:

```bash
pipx install poetry==2.1.4   # or: pip install --user poetry==2.1.4
```

Other options: [Poetry installation](https://python-poetry.org/docs/#installation).

### 3. Install dependencies

```bash
poetry install
```

This creates a virtualenv, installs the dependencies from `poetry.lock`, and installs the project itself so the `local`, `server` and `cron` commands exist.

### 4. Create the `.env` file

The app reads its settings from `.env` in the directory it is started from (the project root). Start from the template:

```bash
cp example-config/.community-server.env .env
```

Fill in the values; see [Environment Variables](#environment-variables) for what each one means.

### 5. Start the server

```bash
poetry run local
```

The API is now at `http://127.0.0.1:5000` and the docs at `http://127.0.0.1:5000/docs`. PostgreSQL, Redis, Keycloak and S3 must be reachable for the routes to work.

---

## Environment Variables

The app is configured via `pydantic-settings` from `.env` or environment. All of the following are **required** unless otherwise noted.

### Core

| Variable             | Required | Description                                                                 |
|----------------------|----------|-----------------------------------------------------------------------------|
| `INSTANCE`           | Yes      | Environment name (e.g. `development`, `staging`, `production`).             |
| `BASE_URL`           | No       | Base URL of the API, used for the code samples in the docs (default: `http://127.0.0.1:5000`). Include the proxy subpath when there is one, e.g. `https://host/community`. |
| `ROOT_PATH`          | No       | Proxy subpath the service is mounted under, e.g. `/community` (default: empty, i.e. served from the root). See [Running behind a reverse proxy subpath](#running-behind-a-reverse-proxy-subpath). |
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
| `S3_ENDPOINT_URL`          | No       | S3-compatible **service** endpoint, not a bucket URL (e.g. `https://pocrakkpc.s3.cyfuture.cloud` — the bucket goes in `*_S3_BUCKET`). Omit for AWS. |
| `S3_ADDRESSING_STYLE`      | No       | `virtual` → `https://bucket.host/key`; `path` → `https://host/bucket/key`. Defaults to what boto3 itself picks: `path` with a custom endpoint, `virtual` for AWS. |
| `S3_PUBLIC_BASE_URL`       | Cond.    | Base URL for browser-facing public object URLs. Falls back to `S3_ENDPOINT_URL` — **one of the two must be set**, there is no built-in default. On AWS set `https://s3.amazonaws.com`. |
| `S3_SIGNATURE_VERSION`     | No       | Presigned-URL signing algorithm. Left to boto3 when unset, which means SigV2 at `us-east-1`. Set `s3v4` only after confirming the provider accepts it. |

### Redis

Three modes are supported: standalone (default), cluster, and sentinel. Enable at most one of `REDIS_CLUSTER_ENABLED` / `REDIS_SENTINEL_ENABLED`.

| Variable                     | Required | Description                                                |
|------------------------------|----------|------------------------------------------------------------|
| `REDIS_URL`                  | Cond.    | Redis URL (e.g. `redis://user:password@host:6379/0`). Required for standalone and cluster mode; ignored in sentinel mode. |
| `REDIS_CLUSTER_ENABLED`      | No       | `true` to connect to a Redis Cluster at `REDIS_URL`. Default `false`. |
| `REDIS_SENTINEL_ENABLED`     | No       | `true` to discover the master through Redis Sentinel. Default `false`. |
| `REDIS_SENTINEL_NODES`       | Cond.    | Sentinel mode: comma-separated sentinel addresses, e.g. `sentinel-0:26379,sentinel-1:26379,sentinel-2:26379`. Port defaults to `26379`. |
| `REDIS_SENTINEL_MASTER_NAME` | No       | Sentinel mode: name of the monitored master. Default `mymaster`. |
| `REDIS_SENTINEL_USERNAME`    | No       | Sentinel mode: username for the sentinels themselves, if they require auth. |
| `REDIS_SENTINEL_PASSWORD`    | No       | Sentinel mode: password for the sentinels themselves, if they require auth. |
| `REDIS_USERNAME`             | No       | Sentinel mode: username for the master. |
| `REDIS_PASSWORD`             | No       | Sentinel mode: password for the master. |
| `REDIS_DB`                   | No       | Sentinel mode: database index. Default `0`. |

### Example `.env` (minimal for local)

```env
INSTANCE=development
BASE_URL=http://127.0.0.1:5000
ROOT_PATH= # Optional: proxy subpath, e.g. /community; leave empty when served from the root
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
S3_ENDPOINT_URL= # Optional: S3-compatible service endpoint; leave empty for AWS
S3_ADDRESSING_STYLE= # Optional: virtual | path (defaults to boto3's own choice)
S3_PUBLIC_BASE_URL=https://s3.amazonaws.com # Required unless S3_ENDPOINT_URL is set
S3_SIGNATURE_VERSION= # Optional: e.g. s3v4, once verified against the provider

REDIS_URL=redis://localhost:6379/0
# Or, for Redis Sentinel (REDIS_URL is then not needed):
# REDIS_SENTINEL_ENABLED=true
# REDIS_SENTINEL_NODES=sentinel-0:26379,sentinel-1:26379,sentinel-2:26379
# REDIS_SENTINEL_MASTER_NAME=mymaster
# REDIS_PASSWORD=<master password>
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

## Cron

A scheduled job publishes competitions whose `scheduled_publish_at` has passed and status is not yet `PUBLISHED`. Use this for automated publishing of pre-scheduled challenges.

**Run manually:**

```bash
poetry run cron
```

**Schedule (e.g. every 5 minutes via cron):**

```bash
*/5 * * * * cd /path/to/dx-community-layer && poetry run cron
```

Requires the same [environment variables](#environment-variables) as the main app (notably `CHALLENGE_DATABASE_URL`, `CHALLENGE_DB_SCHEMA`). Uses the Challenge database only.

---

## Deployments

### 1. Docker (standalone)

**Build:**

```bash
docker build -t dx-community-layer:latest .
```

**Run:**

```bash
docker run -d \
  --name dx-community-layer \
  -p 5000:5000 \
  --env-file .env \
  --restart unless-stopped \
  dx-community-layer:latest
```

Use a `.env` with all [environment variables](#environment-variables) (including `DISCUSSION_DATABASE_URL`, `CHALLENGE_DATABASE_URL`, etc.).

---

### 2. Jenkins (CI/CD)

The `Jenkinsfile` pipeline runs on the `dev` branch and on pull requests (`PR-*`), and only when one of these changed (or the build was started by hand):

- `src/**`, `Dockerfile`, `pyproject.toml`
- `example-config/.community-server.env`
- `stack/postgres/init-scripts/**`

**Steps it performs:**

1. **Build** the Docker image `ghcr.io/datakaveri/dx-community-layer` from the `Dockerfile` (every matching build, including PRs).
2. **Detect config / migration changes** since the last successful build (not on PRs).
3. **Push** the image to GHCR (`dev` only), tagged `1.0.0-<short-commit-hash>` plus:
   - `-C` if `example-config/.community-server.env` changed (new config is needed),
   - `-M` if anything under `stack/postgres/init-scripts/` changed (a DB migration is needed).
4. **Deploy to EKS** (`dev` only) by running `helm upgrade community-server` with the new image tag, using the community-layer chart from the `iudx-installer` repository.
5. **Health check:** `GET https://v2.dev.community-layer.iudx.io/docs` must return `200`, or the build fails.

Build failures on `dev` send an email to the build user, the developers and `$COMMUNITY_LAYER_RECIPIENTS`.

When `example-config/.community-server.env` changes on `dev` or `stable/**`, the separate GitHub Actions workflow `.github/workflows/sync-config.yml` bumps its `CONFIG_VERSION` and syncs the file to `datakaveri/iudx-installer`.

---

### 3. Docker Swarm (stack)

The **app** stack (`stack/app/`) expects Docker **secrets** and uses `entrypoint.sh` to build `DISCUSSION_DATABASE_URL` and `CHALLENGE_DATABASE_URL` from separate DB secrets. The **postgres** and **redis** stacks are separate.

#### Prerequisites

- Docker Swarm initialized.
- External network: `dx-community-network` (`docker network create -d overlay --attachable dx-community-network`).
- PostgreSQL and Redis running and reachable (e.g. via `stack/postgres` and `stack/redis` or your own).

#### 3.1 PostgreSQL stack (if using `stack/postgres`)

```bash
cd stack/postgres
cp secrets.env.example secrets.env
# Edit secrets.env: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
./create-secrets.sh
docker stack deploy -c stack.yml dx-community-postgres
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
    - `S3_ENDPOINT_URL` or `S3_PUBLIC_BASE_URL` (**one is required**), `S3_ADDRESSING_STYLE` (Optional)

   > These three are read from the deploying shell by `stack/app/stack.yml`, not from Docker secrets.
   > For an S3-compatible store, export them before `docker stack deploy`:
   > ```bash
   > export S3_ENDPOINT_URL=https://pocrakkpc.s3.cyfuture.cloud   # service endpoint, NOT a bucket URL
   > ```

2. **Create Docker secrets:**

   ```bash
   ./create-secrets.sh
   ```

3. **Set image in `stack.yml`:**

   Replace `<place-holder>` under `services.app.image` with your image (e.g. `ghcr.io/datakaveri/dx-community-layer:<tag>` or `dx-community-layer:latest`).

4. **Deploy:**

   ```bash
   docker stack deploy -c stack.yml dx-community-app
   ```

The app is exposed on **5000** and uses `/healthz` for healthchecks. `INSTANCE`, `BASE_URL`, `ROOT_PATH`, and `ACTIVATED_SERVICES` are set in `stack.yml`; DB URLs are built by `entrypoint.sh` from the secrets above.

---

### 4. Kubernetes

Example manifests are under `k8s-manifests/app/` (`deploy.yaml`, `service.yaml`, `cronjob.yaml`). The dev environment itself is deployed with the Helm chart in `datakaveri/iudx-installer` (see [Jenkins](#2-jenkins-cicd)).

#### deploy.yaml

- Replace `<placeholder>` for `imagePullSecrets.name` if you use a private registry.
- Replace `<placeholder>` for `containers[0].image` with your image (e.g. `ghcr.io/datakaveri/dx-community-layer:<tag>`).
- Replace `<placeholder>` for `envFrom.secretRef.name` with the name of a **Secret** that contains the same [environment variables](#environment-variables) as key-value pairs.

**Kubernetes Secret example (literal values; prefer sealed-secrets or external secret operators in production):**

```bash
kubectl create secret generic dx-community-secrets --from-literal=INSTANCE=production \
  --from-literal=BASE_URL=https://api.example.com \
  --from-literal=ACTIVATED_SERVICES='["DISCUSSION","CHALLENGE"]' \
  --from-literal=DISCUSSION_DATABASE_URL='postgresql://...' \
  --from-literal=DISCUSSION_DB_SCHEMA=discussion \
  --from-literal=CHALLENGE_DATABASE_URL='postgresql://...' \
  --from-literal=CHALLENGE_DB_SCHEMA=challenge \
  # ... add KEYCLOAK_*, S3_*, REDIS_URL, etc.
```

Then set `envFrom.secretRef.name` to `dx-community-secrets`.

#### service.yaml

- `dx-community-svc` exposes the app on port **80** (targeting container port **5000**). Adjust if your Ingress or network policy expects a different port.

**Apply:**

```bash
kubectl apply -f k8s-manifests/app/deploy.yaml
kubectl apply -f k8s-manifests/app/service.yaml
kubectl apply -f k8s-manifests/app/cronjob.yaml   # scheduled publishing, see Cron
```

#### cronjob.yaml

- `dx-community-cronjob` runs the `cron` command (see [Cron](#cron)) with the same image and Secret. Replace its `<placeholder>` values the same way as in `deploy.yaml`.

---

## Project Structure

```
dx-community-layer/
├── .github/workflows/
│   └── sync-config.yml     # Syncs example-config to iudx-installer
├── example-config/
│   └── .community-server.env  # Template for .env
├── k8s-manifests/app/      # Kubernetes Deployment, Service and CronJob
├── postman/                # Postman collection
├── stack/
│   ├── app/                # Docker Swarm app stack, entrypoint, create-secrets
│   ├── postgres/           # PostgreSQL stack and init scripts
│   └── redis/              # Redis Compose config
├── src/
│   ├── configs/            # DB, env, Redis, S3 config
│   ├── cron/               # Scheduled jobs (e.g. competition publisher)
│   │   └── script.py
│   ├── database/           # Discussion and Challenge models
│   ├── middlewares/        # Auth, logging, search validation
│   ├── routes/             # Challenge, Discussion, utility (incl. /healthz)
│   ├── schemas/            # Pydantic and API schemas
│   ├── services/           # Business logic
│   ├── main.py
│   ├── run.py              # `server` and `local` entrypoints
│   └── docs.py
├── Dockerfile
├── Jenkinsfile             # CI/CD: build, push to GHCR, deploy to EKS
├── LICENSE
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

### Running behind a reverse proxy subpath

Deployments sit behind a proxy that mounts the service under a subpath and **strips**
it before forwarding (e.g. `https://<host>/community/docs` reaches the app as `/docs`).
The app has to be told about that prefix, otherwise the docs page asks the browser for
`/openapi.json` at the root of the host instead of `/community/openapi.json`, and
Swagger UI fails to load the schema.

Set `ROOT_PATH` to the prefix (leading slash, no trailing slash — other spellings are
normalised):

```env
ROOT_PATH=/community
BASE_URL=https://<host>/community
```

`ROOT_PATH` fixes the docs page and adds the prefix to `servers` in the OpenAPI
schema, so **Try it out** calls the right URL. `BASE_URL` is separate: it is what the
copy-pasteable curl/Python/JavaScript samples print, so it needs the prefix too.

Leave `ROOT_PATH` empty when the service is served from the root, including locally.

Full write-up of the failure this prevents, and why `root_path` rather than a relative URL:
[`docs/openapi-docs-behind-subpath.md`](docs/openapi-docs-behind-subpath.md).

---

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE) (`AGPL-3.0-only`).
