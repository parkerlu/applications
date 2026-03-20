#!/bin/bash
set -e

# Start MongoDB in background
mongod --dbpath /data/db --bind_ip 127.0.0.1 --fork --logpath /var/log/mongod.log

# Wait for MongoDB to be ready
for i in $(seq 1 30); do
  if mongosh --quiet --eval "db.runCommand({ping:1})" > /dev/null 2>&1; then
    echo "MongoDB is ready."
    break
  fi
  echo "Waiting for MongoDB... ($i)"
  sleep 1
done

# Start Flask application
exec python3 server.py
