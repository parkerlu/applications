#!/bin/bash
cd "$(dirname "$0")"

# Resolve Docker socket for macOS Docker Desktop if /var/run/docker.sock is absent
if [ ! -S /var/run/docker.sock ] && [ -S "$HOME/.docker/run/docker.sock" ]; then
    export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"
fi

# Start MongoDB if not running
if ! docker compose ps --quiet mongodb 2>/dev/null | grep -q .; then
    echo "Starting MongoDB..."
    docker compose up -d
    sleep 2
fi

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Kill existing server if running
if [ -f .server.pid ]; then
    old_pid=$(cat .server.pid)
    kill "$old_pid" 2>/dev/null
    rm -f .server.pid
fi

# Start server in background
echo "Starting WPP Laptop Request System on http://localhost:8900 ..."
nohup python server.py > .server.log 2>&1 &
echo $! > .server.pid
echo "Server started (PID: $(cat .server.pid))"
