#!/bin/bash
# Celery worker startup script

cd "$(dirname "$0")" || exit 1

echo ""
echo "🔄 Starting Celery worker with Redis broker..."
echo ""

# Load environment variables from .env file
if [[ -f ".env" ]]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Loaded .env file"
fi

# Activate virtual environment
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
fi

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not running"
    exit 1
fi

echo "✅ Redis is running"
echo ""

# Load .env
[[ -f ".env" ]] && set -a && source .env && set +a

# Set defaults
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export CELERY_BROKER_URL="$REDIS_URL"
export FLASK_ENV=production

echo "📍 Broker: $CELERY_BROKER_URL"
echo ""

# Start worker
celery -A app.tasks worker -l info -c 4 --time-limit=600

echo "❌ Celery worker stopped"
