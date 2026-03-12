#!/bin/bash
# Production Startup Script for Linux
# Uses Gunicorn with Uvicorn workers for high-concurrency scaling.

echo "🚀 Starting Automated Recruitment System Backend in Production Mode..."

# Ensure logs directory exists
mkdir -p logs

# Apply SQLite Runtime Tuning
echo "🛠️ Applying SQLite Performance PRAGMAs..."
python3 scripts/optimize_runtime_db.py

# Detect CPU cores
CORES=$(nproc)
WORKERS=$(( (CORES * 2) + 1 ))
echo "📦 Scaling to $WORKERS worker processes..."

# Start with Gunicorn configuration
gunicorn -c gunicorn_conf.py app.main:app
