# Claude Code Memory for discord-epl-goal-clips

## Project Overview
Discord bot that monitors r/soccer for Premier League goal posts and extracts MP4 video links for Discord sharing.

## Deployment
- Lives in `/root/git/discord-epl-goal-clips`
- Deployed via Docker container using `/root/git/vps-tools/cron/update_deploy_epl_clips.sh`
- Auto-deployment runs every minute via cron
- Container name: `epl-clips-bot`
- Force redeploy: `/root/git/vps-tools/cron/update_deploy_epl_clips.sh --force`

## Git Commit Instructions
**IMPORTANT**: Always commit as the user (fenneh), never as Claude.
- Git config is already set to: user.name=fenneh, user.email=justfenyo@gmail.com
- Simply use `git commit` normally - it will use the user's identity automatically
- Never modify git config to change identity

**Commit Message Style**: Use clean, professional commit messages only. Never include:
- AI attribution lines like "🤖 Generated with [Claude Code]"
- Co-authored-by lines for AI
- Marketing-style language
- Long explanatory commit message templates

Examples of good commit messages:
- "Add Brotli dependency for MP4 extraction"
- "Update teams for 2025/26 season" 
- "Fix scoring team detection"

## Key Dependencies
- Brotli>=1.0.9 (required for aiohttp to decode Brotli-compressed responses from streamff.com)

## Common Issues
- MP4 extraction failing with "Can not decode content-encoding: brotli" → Missing Brotli dependency