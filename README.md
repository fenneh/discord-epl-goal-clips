# Goal Bot

Goal Bot is a Python-based Reddit bot that monitors the r/soccer subreddit for posts related to Premier League goals. It identifies relevant posts, checks for duplicate scores, and posts updates to a Discord channel.

## Features

- Monitors r/soccer subreddit for new posts
- Identifies posts containing goal-related keywords and Premier League team names
- Checks for duplicate scores within a 30-second window
- Fetches direct video links from specific sites
- Posts updates to a Discord channel

## Requirements

- Python 3.9
- Docker

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
    ```

3. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

### Running Locally

1. Load the history of posted URLs and scores:
    ```python
    python goal-bot.py
    ```

2. The bot will start monitoring the r/soccer subreddit and posting updates to Discord.

### Running with Docker

1. Build the Docker image:
    ```sh
    ./build.sh
    ```

2. Run the Docker container:
    ```sh
    docker run -d -p 80:80 --env-file .env goal-bot-app
    ```

## File Structure

- `goal-bot.py`: Main script for the bot
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