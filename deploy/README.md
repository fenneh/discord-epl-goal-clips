# Deployment Guide

## Dokku Deployment

The project includes configuration for deploying to Dokku using Docker.

### Prerequisites

- A Dokku server set up and accessible via SSH.
- `dokku` CLI installed locally (optional, but helpful).

### Quick Start

1. Run the setup helper script:
   ```bash
   chmod +x deploy/setup_dokku.sh
   ./deploy/setup_dokku.sh [APP_NAME] [DOKKU_HOST]
   ```
   Example:
   ```bash
   ./deploy/setup_dokku.sh epl-clips soccer-bot.example.com
   ```

   This script will automatically:
   - Disable the legacy cron job deployment
   - Stop the old container
   - Migrate data from `data/` to Dokku storage
   - Create and configure the Dokku app
   - Deploy the new version

2. Follow the instructions output by the script to:
   - Create the app
   - Mount persistent storage (Critical for data persistence!)
   - Set environment variables
   - Push code

### Configuration Files

- `Dockerfile`: Defines the runtime environment.
- `CHECKS`: Health checks for zero-downtime deployment.
- `app.json`: Metadata for the application.
- `.dockerignore`: Excludes unnecessary files from the build.

### Persistence

The application stores state (posted scores/URLs) in the `/app/data` directory inside the container.
For Dokku, we mount a host directory to `/app/data` to ensure this data survives deployments/restarts.

### Environment Variables

Ensure the following are set via `dokku config:set`:
- `CLIENT_ID`
- `CLIENT_SECRET`
- `USER_AGENT`
- `DISCORD_WEBHOOK_URL`
- `DISCORD_USERNAME` (Optional)
- `DISCORD_AVATAR_URL` (Optional)
