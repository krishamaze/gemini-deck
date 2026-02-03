#!/bin/bash
set -e

cd "$(dirname "$0")/.."

# Check for venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing requirements..."
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

# Start Display Services
./scripts/start_display.sh &
DISPLAY_PID=$!

# Start Backend
echo "Starting FastAPI Backend..."
cd backend
python3 main.py
