#!/bin/sh

# DNS is now configured at the docker-compose level
# This entrypoint focuses on database initialization and startup

echo "Initializing database..."
python init_db.py

echo "Starting application..."
exec "$@"

