#!/bin/bash

echo "🏎️  F1 Web Telemetry Viewer"
echo "=========================="
echo
echo "Starting the F1 Telemetry web interface..."
echo "This will open in your browser at: http://localhost:5000"
echo
echo "Press Ctrl+C to stop the server"
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found!"
    echo "   Setting up Python environment..."
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Start the web server
echo "🚀 Starting web server..."
python app.py