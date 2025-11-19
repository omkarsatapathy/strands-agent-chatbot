#!/bin/bash

# Morning Brief Runner Script
# This script ensures proper environment activation and execution

# Exit on error
set -e

# Log file
LOG_DIR="/Users/omkarsatapaphy/Desktop/morning_brief"
mkdir -p "$LOG_DIR"

echo "========================================"
echo "Morning Brief Started: $(date)"
echo "========================================"

# Initialize conda for bash
eval "$(conda shell.bash hook)"

# Activate environment
echo "Activating conda environment: ai_env"
conda activate ai_env

# Verify Python version
echo "Python: $(which python)"
python --version

# Change to project directory
cd /Users/omkarsatapaphy/python_works/agentic_chatbot

# Load environment variables (API keys, etc.)
if [ -f .env ]; then
    echo "Loading environment variables from .env"
    # Handle both KEY=value and KEY = value formats, remove spaces around =
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        # Remove spaces around = and export
        key=$(echo "$line" | cut -d'=' -f1 | tr -d ' ')
        value=$(echo "$line" | cut -d'=' -f2- | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
        export "$key=$value"
        echo "Loaded: $key"
    done < .env
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY is not set!"
    echo "Please check .env file"
    exit 1
fi

echo "Environment variables loaded successfully"

# Run the morning brief script
echo "Starting morning brief generation..."
python src/agent/morning_brief.py

# Check exit status
if [ $? -eq 0 ]; then
    echo "========================================"
    echo "Morning Brief Completed: $(date)"
    echo "========================================"
else
    echo "========================================"
    echo "Morning Brief Failed: $(date)"
    echo "========================================"
    exit 1
fi
