docker build -t goal-bot-app .
docker run -d -p 80:80 --env-file .env goal-bot-app