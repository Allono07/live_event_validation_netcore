#!/bin/sh

# Wait for postgres (simple check)
# In a real production scenario, use a more robust wait-for-it script
# But docker-compose healthcheck handles this for the container startup order

echo "Initializing database..."
python init_db.py

echo "Starting application..."
exec "$@"
