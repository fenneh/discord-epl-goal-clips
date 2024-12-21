#!/bin/bash

echo -e "\033[36mRunning all tests...\033[0m"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run pytest with coverage
echo -e "\n\033[33mRunning pytest with coverage...\033[0m"
pytest --cov=src --cov-report=term-missing -v

# Show test summary
echo -e "\n\033[32mTest Summary:\033[0m"
echo -e "\033[32m============\033[0m"

# Get test files
echo -e "\n\033[36mTest Files:\033[0m"
for file in tests/test_*.py; do
    echo "- $(basename $file)"
done

echo -e "\n\033[32mDone!\033[0m"

# Keep terminal open
echo -e "\nPress any key to exit..."
read -n 1 -s
