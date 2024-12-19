# Premier League Goal Clips Bot - Architecture Guide

## Core Functionality

This bot monitors r/soccer for Premier League goal clips and posts them to Discord. Here are the critical components and their behaviors:

### 1. Post Detection & Filtering

- **Time Window**: Only processes posts from the last 5 minutes to avoid reposting old goals
- **Team Detection**: 
  - Looks for Premier League teams in post titles
  - Uses word boundaries (`\b`) for exact team name matches
  - Example: "Villarreal" should not match "Villa"
  - Teams are configured in `src/config/teams.py` with official names, aliases, colors, and logos

### 2. Score Processing

- **Score Format**: Detects various score patterns:
  - `Team1 [1] - 0 Team2` (scoring team has brackets)
  - `Team1 0 - [1] Team2`
  - `Team1 [1-0] Team2`
- **Duplicate Prevention**:
  - Tracks scores for 5 minutes to prevent duplicates
  - Uses different time windows (30s, 60s, 120s) for different types of duplicates
  - Stored in `posted_scores.pkl`

### 3. Video Extraction

- **Supported Domains**:
  - Check base domains only (e.g., 'streamin', 'streamff', 'dubz')
  - Don't rely on specific TLDs as they change frequently
  - Handle redirects (e.g., streamin.one → streamin.me)
- **MP4 Extraction**:
  - Check meta tags first (`og:video:secure_url`, `og:video`)
  - Fall back to video source elements
  - Retry for up to 5 minutes (30 attempts, 10s delay)

### 4. Discord Integration

- **Embed Format**:
  - Title: Original post title
  - Color: Team's official color (gray for non-PL teams)
  - Thumbnail: Team's official Premier League badge
  - Timestamp: Current UTC time
- **Two-Stage Posting**:
  1. Initial post with clip URL
  2. Follow-up with direct MP4 link when available

## Critical Considerations

1. **Team Matching**:
   - Always use word boundaries for team name matching
   - Consider all possible team name formats
   - Only use Premier League team colors for Premier League teams

2. **Domain Handling**:
   - Never hardcode full domains with TLDs
   - Use base domain matching (e.g., 'streamin' not 'streamin.one')
   - Handle redirects gracefully

3. **Time Management**:
   - Always use UTC for timestamps
   - Only process recent posts (5-minute window)
   - Clean up old scores after 5 minutes

4. **Error Prevention**:
   - Log extensively for debugging
   - Handle network errors gracefully
   - Validate team data before using colors/logos

## Common Pitfalls

1. **❌ DON'T** match team names without word boundaries
2. **❌ DON'T** hardcode specific video host domains/TLDs
3. **❌ DON'T** process posts older than 5 minutes
4. **❌ DON'T** assume a team is Premier League without checking
5. **❌ DON'T** use non-Premier League team colors/logos

## Testing

Key test cases that should always pass:
1. Correct team detection with various score formats
2. No false positives on similar team names
3. Proper handling of redirected video URLs
4. Correct duplicate detection within time windows
5. Proper cleanup of old scores
