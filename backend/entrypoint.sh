#!/bin/bash
set -e

echo "Testing httpx..."
python3 test_httpx.py

echo "Starting API server..."
# Use the command from docker-compose instead of starting uvicorn directly
exec "$@" 