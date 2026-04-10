# SPEC-013: Deployment & Infrastructure

**Status:** Draft
**Priority:** P1
**Phase:** 6 (Week 13) for production; Phase 1 (Week 1) for development
**Dependencies:** All other specs

---

## 1. Overview

Quorum runs as a containerized application stack on a VPS. Development uses Docker Compose locally; production uses the same containers with production-grade configuration, systemd services, and a reverse proxy with automatic TLS.

## 2. Development Environment

### 2.1 docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: paperpilot
      POSTGRES_USER: paperpilot
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U paperpilot"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      DATABASE_URL: postgresql+asyncpg://paperpilot:dev_password@postgres:5432/paperpilot
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_SECURE: "false"
      JWT_SECRET: dev-jwt-secret-change-in-production
      ENCRYPTION_KEY: dev-encryption-key-32-bytes-long!
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    volumes:
      - ./backend:/app/backend
      - ./agents:/app/agents

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_WS_URL: ws://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app/frontend

volumes:
  postgres_data:
  minio_data:
```

### 2.2 Dockerfile.backend

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Tectonic
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Tectonic
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
ENV PATH="/root/.local/bin:$PATH"

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY agents/ ./agents/

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 2.3 Dockerfile.frontend

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .

CMD ["npm", "run", "dev"]
```

## 3. Production Environment

### 3.1 VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 100 GB SSD | 200 GB SSD |
| OS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| Network | 100 Mbps | 1 Gbps |

### 3.2 docker-compose.prod.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend.prod
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MINIO_SECURE: "false"
      JWT_SECRET: ${JWT_SECRET}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      TELEGRAM_WEBHOOK_URL: ${TELEGRAM_WEBHOOK_URL}
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      - postgres
      - redis
      - minio
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 4G

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend.prod
    environment:
      NEXT_PUBLIC_API_URL: ${PUBLIC_API_URL}
      NEXT_PUBLIC_WS_URL: ${PUBLIC_WS_URL}
    ports:
      - "127.0.0.1:3000:3000"
    depends_on:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:
  caddy_data:
  caddy_config:
```

### 3.3 Caddyfile

```
paperpilot.example.com {
    handle /api/* {
        reverse_proxy backend:8000
    }

    handle /ws {
        reverse_proxy backend:8000
    }

    handle /webhook/* {
        reverse_proxy backend:8000
    }

    handle {
        reverse_proxy frontend:3000
    }
}
```

### 3.4 Production Backend Dockerfile

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl build-essential pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY agents/ ./agents/

ENV PATH="/root/.local/bin:$PATH"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3.5 Production Frontend Dockerfile

```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

ENV NODE_ENV=production
EXPOSE 3000

CMD ["node", "server.js"]
```

## 4. Environment Variables

### 4.1 .env.example

```bash
# Database
POSTGRES_DB=paperpilot
POSTGRES_USER=paperpilot
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD

# Redis
REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD

# MinIO
MINIO_ACCESS_KEY=CHANGE_ME_MINIO_KEY
MINIO_SECRET_KEY=CHANGE_ME_MINIO_SECRET

# Security
JWT_SECRET=CHANGE_ME_64_CHAR_RANDOM_STRING
ENCRYPTION_KEY=CHANGE_ME_32_BYTE_ENCRYPTION_KEY

# URLs (production)
PUBLIC_API_URL=https://paperpilot.example.com/api/v1
PUBLIC_WS_URL=wss://paperpilot.example.com/ws
TELEGRAM_WEBHOOK_URL=https://paperpilot.example.com/webhook/telegram
```

### 4.2 Secret Generation

```bash
# JWT Secret (64 chars)
openssl rand -hex 32

# Encryption Key (32 bytes, base64)
openssl rand -base64 32

# Postgres password
openssl rand -hex 16

# Redis password
openssl rand -hex 16
```

## 5. Backup Strategy

### 5.1 Database Backup

```bash
#!/bin/bash
# scripts/backup-db.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="paperpilot_${TIMESTAMP}.sql.gz"

docker exec paperpilot-postgres-1 \
  pg_dump -U paperpilot paperpilot | gzip > "/backups/db/${BACKUP_FILE}"

# Upload to MinIO backup bucket
mc cp "/backups/db/${BACKUP_FILE}" minio/backups/db/

# Retain 30 daily backups
find /backups/db/ -name "*.sql.gz" -mtime +30 -delete
```

### 5.2 MinIO Backup

MinIO data is on a Docker volume. Back up the volume:

```bash
#!/bin/bash
# scripts/backup-files.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

docker run --rm \
  -v paperpilot_minio_data:/data \
  -v /backups/minio:/backup \
  alpine tar czf "/backup/minio_${TIMESTAMP}.tar.gz" /data
```

### 5.3 Automated Schedule

```bash
# /etc/cron.d/paperpilot-backup
0 2 * * * root /opt/paperpilot/scripts/backup-db.sh
0 3 * * 0 root /opt/paperpilot/scripts/backup-files.sh
```

## 6. Monitoring

### 6.1 Health Checks

```python
# backend/app/api/health.py
@router.get("/health")
async def health():
    checks = {
        "database": await check_db(),
        "redis": await check_redis(),
        "minio": await check_minio(),
    }
    all_healthy = all(checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### 6.2 Logging

Structured JSON logging for all components:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "agent_task_completed",
    agent_id=agent_id,
    task_id=task_id,
    model=model_used,
    tokens_input=input_tokens,
    tokens_output=output_tokens,
    cost_usd=cost,
    duration_seconds=duration,
)
```

### 6.3 Optional: Grafana Stack

For advanced monitoring:
- **Grafana Loki**: Log aggregation (ingest from Docker log driver)
- **Grafana**: Dashboard visualization
- **Prometheus**: Metrics collection (FastAPI metrics endpoint)

## 7. Update / Deployment Process

```bash
# On VPS
cd /opt/paperpilot

# Pull latest code
git pull origin main

# Rebuild containers
docker compose -f docker-compose.prod.yml build

# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Restart services (zero-downtime with rolling updates)
docker compose -f docker-compose.prod.yml up -d

# Verify health
curl https://paperpilot.example.com/api/v1/health
```

## 8. Security Hardening

| Measure | Implementation |
|---------|---------------|
| Firewall | UFW: allow 22 (SSH), 80, 443 only |
| SSH | Key-only auth, disable password login |
| Docker | Run containers as non-root users |
| TLS | Auto-managed by Caddy (Let's Encrypt) |
| Database | Not exposed on public ports (Docker network only) |
| Redis | Password-protected, Docker network only |
| MinIO | Docker network only; accessed via presigned URLs |
| API Keys | AES-256 encrypted at rest in database |
| JWT | 24-hour expiry, refresh token rotation |
| CORS | Restricted to dashboard domain |
| Rate Limiting | Auth endpoints: 5 req/min; API: 100 req/min |

## 9. Cost Estimate (Infrastructure)

| Component | Provider | Monthly Cost |
|-----------|----------|-------------|
| VPS (8 CPU, 16GB RAM) | Hetzner / DigitalOcean | $40-80 |
| Domain name | Any registrar | ~$1 |
| Backups (extra storage) | Included or ~$5 | $0-5 |
| **Total infrastructure** | | **$41-86/month** |
| Claude API tokens | Anthropic | $150-300/month |
| **Total operational** | | **~$200-400/month** |
