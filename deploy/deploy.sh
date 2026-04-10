#!/bin/bash
set -euo pipefail

APP_DIR="/opt/quorum"
REPO_URL="https://github.com/ThirunagariHarish/Quorum.git"
BRANCH="main"

echo "=== Quorum Deployment ==="
echo "$(date '+%Y-%m-%d %H:%M:%S')"

if [ ! -d "$APP_DIR" ]; then
    echo ">> First deploy: cloning repo..."
    git clone "$REPO_URL" "$APP_DIR"
else
    echo ">> Pulling latest changes..."
    cd "$APP_DIR"
    git fetch origin
    git reset --hard "origin/$BRANCH"
fi

cd "$APP_DIR"

if [ ! -f .env.production ]; then
    echo "ERROR: .env.production not found in $APP_DIR"
    echo "Create it from .env.production.template first!"
    exit 1
fi

echo ">> Building and starting services..."
docker compose -f docker-compose.prod.yml --env-file .env.production up --build -d

echo ">> Waiting for services to be healthy..."
sleep 10

echo ">> Checking health..."
if curl -sf http://localhost:80/api/v1/health > /dev/null 2>&1; then
    echo ">> Deployment successful! Health check passed."
else
    echo ">> WARNING: Health check failed. Checking container status..."
    docker compose -f docker-compose.prod.yml ps
fi

echo ">> Cleaning up old images..."
docker image prune -f

echo "=== Deployment complete ==="
