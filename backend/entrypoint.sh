#!/bin/bash
set -e

echo "Testing httpx..."
python3 test_httpx.py

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 