#!/bin/bash
cd "$(dirname "$0")"

if [ -f .server.pid ]; then
    pid=$(cat .server.pid)
    if kill "$pid" 2>/dev/null; then
        echo "Server stopped (PID: $pid)"
    else
        echo "Server was not running"
    fi
    rm -f .server.pid
else
    echo "No server PID file found"
fi
