# Goal Bot

Goal Bot is a Python-based Reddit bot that monitors the r/soccer subreddit for posts related to Premier League goals. It identifies relevant posts, checks for duplicate scores, and posts updates to a Discord channel.

## Features

- Monitors r/soccer subreddit for new posts
- Identifies posts containing goal-related keywords and Premier League team names
- Checks for duplicate scores within a 30-second window
- Fetches direct video links from supported sites:
  - streamff.co
  - streamin.one
  - dubz.link
- Posts updates to a Discord channel with rich embeds
- Automatic retry mechanism for failed video extractions
- Score normalization and duplicate detection
- Rate limit monitoring for Reddit API
- Configurable logging
- Test modes for development and debugging

## Requirements

- Python 3.9
- Docker

## Configuration

The bot can be configured using environment variables in your `.env` file:

```env
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
USER_AGENT=your_user_agent
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DISCORD_USERNAME=your_webhook_username        # Optional: defaults to 'Ally'
DISCORD_AVATAR_URL=your_webhook_avatar_url    # Optional: defaults to preset image
```

Additional configuration options are available in the code:
- Goal detection keywords
- Premier League team names and aliases
- Supported video hosting sites
- Score matching patterns

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/fenneh/discord-epl-goal-clips.git
    cd discord-epl-goal-clips
    ```

2. Create a `.env` file with your Reddit API credentials and Discord webhook URL:
    ```env
    CLIENT_ID=your_client_id
    CLIENT_SECRET=your_client_secret
    USER_AGENT=your_user_agent
    DISCORD_WEBHOOK_URL=your_discord_webhook_url
    DISCORD_USERNAME=your_webhook_username        # Optional: defaults to 'Ally'
    DISCORD_AVATAR_URL=your_webhook_avatar_url    # Optional: defaults to preset image
    ```

3. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

### Running Locally

1. Load the history of posted URLs and scores:
    ```python
    python goal_bot.py
    ```

2. The bot will start monitoring the r/soccer subreddit and posting updates to Discord.

### Test Modes

The bot includes several test modes for development and debugging:

1. Reprocess historical posts:
    ```sh
    python goal_bot.py --test 24  # Reprocess posts from last 24 hours
    ```

2. Send a single test post:
    ```sh
    python goal_bot.py --test-post
    ```

3. Debug URL processing:
    ```sh
    python goal_bot.py --debug-urls  # Test URL extraction without posting to Discord
    ```

The debug mode performs the following validations:
- Ensures all URLs start with `https://`
- Validates URLs with HEAD requests to confirm accessibility
- Removes URL fragments (e.g., `#t=0.1`) that can cause playback issues
- Shows detailed logging of URL processing and validation

### URL Processing

The bot supports extracting video URLs from these sources:
- `streamff.co` -> `https://ffedge.streamff.com/uploads/[id].mp4`
- `streamin.one` -> `https://streamin.fun/uploads/[id].mp4`
- `dubz.link` -> `https://cdn.squeelab.com/guest/videos/[id].mp4`

Each URL is validated before posting to ensure:
1. Complete URL format (https://)
2. Accessibility (200 status code)
3. Clean format (no fragments or malformed components)

### Running with Docker

1. Build the Docker image:
    ```sh
    docker build -t goal-bot .
    ```

2. Run the container:
    ```sh
    docker run -d --name goal-bot --env-file .env goal-bot
    ```

## Troubleshooting

Common issues and solutions:

1. **Missing Video Links**: The bot will automatically retry failed video extractions for supported sites.
2. **Rate Limits**: The bot monitors Reddit API rate limits and logs relevant information.
3. **Duplicate Posts**: Posts with similar scores within 30 seconds are automatically filtered.

## Development

The bot uses several helper functions for processing:
- Score normalization and duplicate detection
- Team name matching with aliases
- Video URL extraction for supported sites
- Discord webhook formatting

## Testing

The bot includes a comprehensive test suite in `test_goal_bot.py` that verifies key functionality:

### Running Tests

Run the test suite using:
```sh
python -m unittest test_goal_bot.py -v
```

### Test Coverage

The test suite covers:

1. Score Pattern Normalization
   - Handles abbreviated vs. full player names (e.g., "E. Haaland" vs "Erling Haaland")
   - Normalizes case and whitespace
   - Processes different score formats (home/away team scoring)

2. Duplicate Detection
   - Validates same goal with different player name formats
   - Ensures different goals are not marked as duplicates
   - Checks goals with same minute but different scores
   - Verifies goals with same teams but different scorers

### Test Cases

Example test scenarios:
```python
# Same goal, different player name formats (should be duplicate)
"Crystal Palace 1 - [1] Manchester City - E. Haaland 30'"
"Crystal Palace 1 - [1] Manchester City - Erling Haaland 30'"

# Different goals (should not be duplicate)
"Crystal Palace 1 - [1] Manchester City - E. Haaland 30'"
"Crystal Palace [2] - 1 Manchester City - M. Lacroix 56'"
```

Each test case uses isolated state to ensure consistent results, and includes detailed logging for debugging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## File Structure

- `goal_bot.py`: Main script for the bot
- `requirements.txt`: List of required Python packages
- `Dockerfile`: Docker configuration
- `build.sh`: Script to build and run the Docker container
- `.env`: Environment variables for Reddit API credentials and Discord webhook URL
- `posted_urls.pkl`: Pickle file to store posted URLs
- `posted_scores.pkl`: Pickle file to store posted scores

## Functions

- `load_history()`: Load the history of posted URLs and scores from disk
- `save_history()`: Save the history of posted URLs and scores to disk
- `contains_goal_keyword(title)`: Check if the post title contains any goal-related keywords or patterns
- `contains_specific_site(url)`: Check if the URL contains any of the specific sites
- `contains_premier_league_team(title)`: Check if the post title contains any Premier League team names or aliases
- `get_direct_video_link(url)`: Fetch the direct video link from the page
- `post_to_discord(message)`: Send a message to the Discord webhook
- `is_duplicate_score(title, timestamp)`: Check if the same score for the same game is posted within 30 seconds

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.