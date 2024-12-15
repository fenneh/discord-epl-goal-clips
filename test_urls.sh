#!/bin/bash

# Test URLs for the goal bot
urls=(
    "1hf0otj" # Southampton vs Tottenham
    "1hf1pul" # Chelsea vs Brentford
    "1hex1o2" # Man City vs Man United
    "1he6l29" # Wolves vs Ipswich
)

echo -e "\e[32mTesting URLs...\e[0m"
echo -e "\e[32m----------------\e[0m"

for url in "${urls[@]}"; do
    echo -e "\n\e[33mTesting thread: $url\e[0m"
    python -m src.main --test-threads "$url" --ignore-posted --ignore-duplicates
    
    echo -e "\n\e[36mPress Enter to continue to next URL...\e[0m"
    read
done

echo -e "\n\e[32mAll tests complete!\e[0m"
