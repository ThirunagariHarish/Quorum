# Quorum VPS Setup Guide

Target: Ubuntu VPS at `187.124.77.249`

## Step 1: SSH into VPS and install Docker

```bash
ssh root@187.124.77.249

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
docker --version

# Install Docker Compose plugin (if not included)
apt install -y docker-compose-plugin
docker compose version

# Install git
apt install -y git
```

## Step 2: Generate an SSH key pair for GitHub Actions

Run this **on your Mac** (not the VPS):

```bash
ssh-keygen -t ed25519 -C "quorum-deploy" -f ~/.ssh/quorum_deploy -N ""
```

Then copy the **public** key to the VPS:

```bash
ssh-copy-id -i ~/.ssh/quorum_deploy.pub root@187.124.77.249
```

Verify you can connect without a password:

```bash
ssh -i ~/.ssh/quorum_deploy root@187.124.77.249 "echo OK"
```

## Step 3: Add GitHub Secrets

Go to: https://github.com/ThirunagariHarish/Quorum/settings/secrets/actions

Add these repository secrets:

| Secret Name    | Value                                              |
|----------------|-----------------------------------------------------|
| `VPS_HOST`     | `187.124.77.249`                                   |
| `VPS_USER`     | `root`                                             |
| `VPS_SSH_KEY`  | Contents of `~/.ssh/quorum_deploy` (the PRIVATE key) |

To copy the private key:

```bash
cat ~/.ssh/quorum_deploy | pbcopy
```

## Step 4: Create .env.production on the VPS

SSH into the VPS and create the environment file:

```bash
ssh root@187.124.77.249

mkdir -p /opt/quorum
cat > /opt/quorum/.env.production << 'EOF'
POSTGRES_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
MINIO_ACCESS_KEY=quorum-minio-admin
MINIO_SECRET_KEY=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 16)
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
PUBLIC_API_URL=http://187.124.77.249/api
PUBLIC_WS_URL=ws://187.124.77.249/ws
EOF
```

**Important**: Replace `sk-ant-YOUR-KEY-HERE` with your actual Anthropic API key.

To generate secrets with real random values:

```bash
ssh root@187.124.77.249 bash -c '
mkdir -p /opt/quorum
cat > /opt/quorum/.env.production << ENVEOF
POSTGRES_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
MINIO_ACCESS_KEY=quorum-minio-admin
MINIO_SECRET_KEY=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 16)
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
PUBLIC_API_URL=http://187.124.77.249/api
PUBLIC_WS_URL=ws://187.124.77.249/ws
ENVEOF
echo "Created .env.production with random secrets"
cat /opt/quorum/.env.production
'
```

## Step 5: Trigger First Deploy

Either push to `main` to trigger GitHub Actions, or manually deploy:

```bash
ssh root@187.124.77.249 bash -c '
cd /opt/quorum
git clone https://github.com/ThirunagariHarish/Quorum.git . || (git fetch origin && git reset --hard origin/main)
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d
'
```

## Step 6: Verify

```bash
# From your Mac
curl http://187.124.77.249/api/v1/health
```

Expected response:
```json
{"status": "healthy", "checks": {"database": true, "redis": true}}
```

The dashboard will be at: **http://187.124.77.249**

## How CI/CD Works

```
Push to main → GitHub Actions → SSH into VPS → git pull → docker compose up --build -d
```

Every push to `main` automatically deploys to the VPS. No webhook server needed -- GitHub Actions SSHes directly into the VPS.

## Firewall (optional but recommended)

```bash
ssh root@187.124.77.249 bash -c '
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
'
```
