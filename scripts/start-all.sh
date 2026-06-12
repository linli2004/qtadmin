#!/bin/bash
# Start all qtadmin services for development
# Provider API → :8080  |  Demo frontend → :8000

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

cleanup() {
    echo ""
    echo "Stopping all services..."
    pkill -f "uvicorn app.__main__:app" 2>/dev/null || true
    pkill -f "examples/human/app.py" 2>/dev/null || true
    echo "All services stopped."
}
trap cleanup EXIT

# Start provider
echo "Starting Provider API on :8080..."
cd "$PROJECT_DIR/src/provider"
.venv/bin/uvicorn app.__main__:app --host 0.0.0.0 --port 8080 &
PROVIDER_PID=$!
echo "  Provider PID: $PROVIDER_PID"

# Wait for provider to be ready
sleep 2

# Start demo
echo "Starting Demo frontend on :8000..."
cd "$PROJECT_DIR"
python examples/human/app.py &
DEMO_PID=$!
echo "  Demo PID: $DEMO_PID"

echo ""
echo "=== All services started ==="
echo "  Provider API:  http://localhost:8080"
echo "  Demo frontend: http://localhost:8000"
echo "  Health check:  http://localhost:8080/health"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for any process to exit
wait
