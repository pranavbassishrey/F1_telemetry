#!/bin/bash

echo "Starting F1 Web Telemetry Application..."
echo "========================================"
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and start Flask app
source .venv/bin/activate

echo "Starting Flask server on http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo

# Start the Flask application
python app.py