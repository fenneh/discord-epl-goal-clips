# Discord EPL Goal Clips Bot

Monitors r/soccer for Premier League goal posts and shares MP4 clips to Discord.

## Setup

1. Create `.env` file:
```env
CLIENT_ID=your_reddit_client_id
CLIENT_SECRET=your_reddit_client_secret
USER_AGENT=your_user_agent
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

2. Run:
```bash
pip install -r requirements.txt
python -m src.main
```

## Features

- Monitors r/soccer for PL goal posts
- Extracts MP4 links from video hosts
- Posts to Discord with team colors/logos
- Duplicate detection
- Auto-retry for failed extractions

## Supported Video Hosts

- streamff.com/live
- streamin.one/me/fun
- dubz.link
- streamable.com