#!/bin/bash
# start.sh - Launch script for Hugging Face Spaces

# Start the Mock API server in the background
uvicorn mock_api.server:app --host 0.0.0.0 --port 7861 &
MOCK_PID=$!

# Wait for it to start
sleep 2

# Start the OpenEnv server in the foreground so Docker doesn't exit
uvicorn server.app:app --host 0.0.0.0 --port 7860
