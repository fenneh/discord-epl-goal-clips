# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for persistence
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080

# Required environment variables:
# - CLIENT_ID: Reddit API client ID
# - CLIENT_SECRET: Reddit API client secret
# - USER_AGENT: Reddit API user agent
# - DISCORD_WEBHOOK_URL: Discord webhook URL
# Optional environment variables:
# - DISCORD_USERNAME: Bot username (default: 'Ally')
# - DISCORD_AVATAR_URL: Bot avatar URL (has default)
# - PORT: Port to run on (default: 8080)

# Run the FastAPI application when the container launches
CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT"]