# Goal Bot

Goal Bot is a Python-based Reddit bot that monitors the r/soccer subreddit for posts related to Premier League goals. It identifies relevant posts, checks for duplicate scores, and posts updates to a Discord channel.

## Features

- Monitors r/soccer subreddit for new posts
- Identifies posts containing goal-related keywords and Premier League team names
- Advanced duplicate detection:
  - Exact URL matches within 30s
  - Exact score/minute/scorer matches within 60s (handles name variations)
  - Similar minute matches (±1) within 120s
- Fetches direct video links from supported sites:
  - streamff.com / streamff.live
  - streamin.one / streamin.fun
  - dubz.link
- Posts updates to Discord:
  - Direct MP4 links for video files
  - Rich embeds for regular links with team colors and logos
- Automatic retry mechanism for failed video extractions
- Comprehensive logging with status indicators
- Rate limit monitoring for Reddit API
- Test modes for development and debugging

## Requirements

- Python 3.9+
- Docker (optional)

## Configuration

The bot can be configured using environment variables in your `.env` file:

```env
# Reddit API Configuration
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
USER_AGENT=your_user_agent

# Discord Configuration
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DISCORD_USERNAME=your_webhook_username        # Optional: defaults to 'Ally'
DISCORD_AVATAR_URL=your_webhook_avatar_url    # Optional: defaults to preset image

# Bot Settings
POST_AGE_MINUTES=5                           # Optional: defaults to 5
LOG_LEVEL=INFO                               # Optional: defaults to INFO
```

Additional configuration options are available in the code:
- Goal detection keywords and patterns
- Premier League team names and aliases
- Supported video hosting sites
- Score matching patterns
- Duplicate detection time windows

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/fenneh/discord-epl-goal-clips.git
    cd discord-epl-goal-clips
    ```

2. Create a `.env` file with your configuration (see above)

3. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Install development dependencies (optional):
    ```sh
    pip install -r requirements-dev.txt
    ```

## Usage

### Running Locally

Start the bot:
```sh
python -m src.main
```

The bot will:
1. Monitor r/soccer for new Premier League goal posts
2. Extract video links and check for duplicates
3. Post updates to Discord with direct MP4 links when possible

### Testing

Run the test suite:
```sh
# Windows
.\run_tests.ps1

# Linux/Mac
./run_tests.sh
```

Test specific functionality:
```python
# Test posts from last X hours
python -m src.main --test-hours 24

# Test specific Reddit threads
python -m src.main --test-threads "abc123,xyz789"

# Test with duplicate checking disabled
python -m src.main --ignore-duplicates
```

## Logging

The bot uses structured logging with clear status indicators:
- `[INFO]` - General information and successful operations
- `[SKIP]` - Posts that were skipped with reason
- `[DUPLICATE]` - Detailed duplicate detection information

Logs include:
- Timestamps
- Reddit and video URLs
- Processing status and decisions
- Duplicate detection details

## Recent Changes

### 2024-12-19
- Enhanced duplicate detection with time windows
- Improved player name normalization
- Added comprehensive test suite
- Organized test files into dedicated directory
- Added pytest-asyncio for async test support
- Fixed domain extraction and validation

### 2024-12-20
- Updated README with recent changes and roadmap
- Improved documentation for configuration and usage

## Future Roadmap

### Planned Features
1. Support for "miss" posts
   - Track near misses and big chances
   - Different Discord channel/formatting

2. Support for red card incidents
   - Track red cards and second yellows
   - Different Discord channel/formatting

### Technical Improvements
1. Improve video host reliability
2. Add more test coverage
3. Monitor and improve duplicate detection accuracy

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.