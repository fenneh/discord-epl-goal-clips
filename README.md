# discord-epl-goal-clips

Discord bot that monitors r/soccer for Premier League goal clips and posts them to Discord with team branding. Also provides match day notifications via ESPN.

## Features

- Monitors r/soccer for PL goal posts in real-time
- Extracts MP4 links from video hosts (streamff, streamin, dubz, streamable)
- Posts to Discord with team colors and logos
- Duplicate detection to prevent spam
- Daily match schedule at 8am UK
- Kick-off notifications (batched by time slot)
- Full-time score notifications
- ESPN goal fallback when Reddit is slow

## Setup

Create a `.env` file:

```
CLIENT_ID=reddit_client_id
CLIENT_SECRET=reddit_client_secret
USER_AGENT=reddit_user_agent
DISCORD_WEBHOOK_URL=discord_webhook_url
```

## Run

```
uv sync --frozen
uv run python -m src.main
```

## Docker

```
docker build -t epl-clips .
docker run --env-file .env epl-clips
```

## Deployment

Deployed via Dokku with GitHub Actions CI/CD. See `.github/workflows/deploy.yml`.
