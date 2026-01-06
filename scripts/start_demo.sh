#!/bin/bash
# Shell script to start FinDataExtractorDEMO (Linux/Mac)
# Sources invoices from FinDataExtractor/data

set -e

echo "========================================"
echo "FinDataExtractorDEMO Startup"
echo "========================================"
echo ""

# Check if demo database exists
DEMO_DB="findataextractor_demo.db"
if [ ! -f "$DEMO_DB" ]; then
    echo "Demo database not found. Running setup..." 
    export DEMO_MODE="true"
    export DATABASE_URL="sqlite+aiosqlite:///./findataextractor_demo.db"
    python scripts/setup_demo.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Setup failed!"
        exit 1
    fi
    echo ""
fi

# Set environment variables
export DEMO_MODE="true"
export DATABASE_URL="sqlite+aiosqlite:///./findataextractor_demo.db"

echo "Starting services..."
echo "  DEMO_MODE: $DEMO_MODE"
echo "  DATABASE_URL: $DATABASE_URL"
echo ""

# Start API server in background
echo "Starting API Server..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
echo "  API Server PID: $API_PID"
echo "  API Server: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"

# Wait for API server to start
sleep 4

# Start Streamlit UI
echo ""
echo "Starting Streamlit UI..."
echo "  Streamlit UI: http://localhost:8501"
streamlit run streamlit_app.py --server.port 8501 --server.address localhost

# Cleanup on exit
trap "kill $API_PID 2>/dev/null" EXIT

