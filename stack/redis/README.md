This directory contains the Docker Compose configuration for deploying Redis cache server for the TGDex Discussion application.

## Overview

The Redis service is deployed with:

- Redis 8.2 Alpine image
- Access Control List (ACL) for user authentication

## Files

- `compose.yml` - Docker Compose configuration
- `redis.conf` - Redis server configuration
- `users.acl` - Redis ACL (Access Control List) for user authentication

## Setup

### 1. Configure ACL Users

Edit `users.acl` to set up Redis users:

```bash
# Default format:
# user <username> on ><password> ~<key-pattern> &<channel-pattern> +<commands>
```

The default configuration disables the default user and creates a sample user. You should:

1. Change the username from `changeme` to your desired username
2. Change the password from `changeme` to a strong password
3. Optionally adjust permissions (currently allows all commands except dangerous ones)

Example:

```
user default off
user myapp on >MyStr0ngP@ssw0rd ~* &* +@all -@dangerous
```

### 2. Configure Redis Settings (Optional)

The `redis.conf` file contains:

- TCP keepalive: 120 seconds
- Save policies:
  - Save after 900 seconds if at least 1 key changed
  - Save after 300 seconds if at least 10 keys changed
  - Save after 60 seconds if at least 10000 keys changed
- Data persistence directory: `/data`

You can modify these settings based on your requirements.

### 3. Start Redis

```bash
docker compose up -d
```

## Configuration

### Redis Settings

The Redis server is configured with:

- **TCP Keepalive**: 120 seconds for connection health
- **Persistence**: Automatic saving based on key changes
- **ACL**: User-based authentication with permission control
- **Data Directory**: `/data` (mapped to Docker volume)

### Resources

No specific resource limits are set. Configure them in `compose.yml` if needed:

```yaml
deploy:
  resources:
    limits:
      cpus: "1"
      memory: 512M
```

## Ports

Redis is exposed on the standard port `6379`.

## Management

### View Container Status

```bash
docker ps | grep redis-nova
```

### View Logs

```bash
docker logs -f redis-nova
```

### Connect to Redis CLI

```bash
docker exec -it redis-nova redis-cli
```

Then authenticate:

```
AUTH <username> <password>
```

### Test Connection

```bash
docker exec -it redis-nova redis-cli -a <password> --user <username> PING
```

### Stop Redis

```bash
docker compose down
```

## Troubleshooting

### Connection Refused

Check if Redis is running:

```bash
docker ps | grep redis-nova
```

### Authentication Failed

Verify credentials in `users.acl` match your connection string.

### Permission Denied

Check ACL permissions:

```bash
docker exec -it redis-nova redis-cli ACL LIST
```
