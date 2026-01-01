#!/bin/bash
set -e

# Configuration
APP_NAME="${1:-epl-clips}"
OLD_CONTAINER_NAME="epl-clips-bot"
OLD_DATA_DIR="/root/git/discord-epl-goal-clips/data"
DOKKU_HOST="${2:-localhost}" # Default to localhost usually for local dokku, but user might be remote. 
# Check if we are ON the dokku server or deploying TO it.
# The user seems to be on the server itself (root@...).
# If we are on the server, we can run dokku commands directly if the `dokku` user/group is set up or via `dokku` command.

# Since 'which dokku' failed earlier, we might not be on the machine with dokku installed, 
# OR dokku is not in the path. But the user said "I want to ... use dokku".
# If dokku is not installed, this script can't magically make it work.
# However, assuming the user *will* run this on the server where dokku is (or installs it).

echo "=================================================="
echo "Dokku Migration & Setup for $APP_NAME"
echo "=================================================="

# 1. Stop and Disable Legacy Deployment
echo "Step 1: Checking for legacy deployment..."

# Disable Cron
if crontab -l | grep -q "update_deploy_epl_clips.sh"; then
    echo "Files in crontab detected. Commenting out legacy cron job..."
    crontab -l | sed 's|^.*update_deploy_epl_clips.sh|# &|' | crontab -
    echo "Cron job disabled."
else
    echo "No active cron job found for epl-clips."
fi

# Stop Container
if docker ps -q -f name=$OLD_CONTAINER_NAME > /dev/null; then
    echo "Stopping legacy container $OLD_CONTAINER_NAME..."
    docker stop $OLD_CONTAINER_NAME
    echo "Container stopped."
else
    echo "Legacy container not running."
fi

# 2. Prepare Dokku App
echo ""
echo "Step 2: Preparing Dokku App..."

# Check if dokku command exists locally
if ! command -v dokku &> /dev/null; then
    echo "Dokku command not found. Are you running this on the Dokku server?"
    echo "If this is a remote deployment, please run the app creation commands manually on the server:"
    echo "  dokku apps:create $APP_NAME"
    echo "  mkdir -p /var/lib/dokku/data/storage/$APP_NAME"
    echo "  chown -R 32767:32767 /var/lib/dokku/data/storage/$APP_NAME"
    echo "  dokku storage:mount $APP_NAME /var/lib/dokku/data/storage/$APP_NAME:/app/data"
    echo "  dokku config:set $APP_NAME --no-restart $(cat .env | grep -v '^#' | xargs)"
    exit 1
fi

dokku apps:create $APP_NAME || true

# 3. Data Migration
echo ""
echo "Step 3: Migrating Data..."
DOKKU_STORAGE_DIR="/var/lib/dokku/data/storage/$APP_NAME"

# Create storage dir
mkdir -p "$DOKKU_STORAGE_DIR"

# Copy data if old data exists
if [ -d "$OLD_DATA_DIR" ] && [ ! -z "$(ls -A $OLD_DATA_DIR)" ]; then
    echo "Copying data from $OLD_DATA_DIR to $DOKKU_STORAGE_DIR..."
    cp -r $OLD_DATA_DIR/* "$DOKKU_STORAGE_DIR/"
    echo "Data migrated."
else
    echo "No legacy data found to migrate."
fi

# Set permissions for Herokuish user (ID 32767)
echo "Setting permissions..."
chown -R 32767:32767 "$DOKKU_STORAGE_DIR"

# Mount storage
dokku storage:mount $APP_NAME "$DOKKU_STORAGE_DIR:/app/data"

# 4. Configuration
echo ""
echo "Step 4: Configuring Environment..."
if [ -f .env ]; then
    dokku config:set $APP_NAME --no-restart $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. You will need to set config manually."
fi

dokku checks:enable $APP_NAME

# 5. Deployment
echo ""
echo "Step 5: Deploying..."
echo "Adding dokku remote..."
if ! git remote | grep -q dokku; then
    git remote add dokku dokku@localhost:$APP_NAME
fi

echo "Pushing to Dokku..."
# Assuming we are on the server and can push to localhost
git push dokku main

echo ""
echo "=================================================="
echo "Migration Complete!"
echo "App should be running at: http://$(dokku domains:report $APP_NAME --quiet)"
echo "=================================================="
