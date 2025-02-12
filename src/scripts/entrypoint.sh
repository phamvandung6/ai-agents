#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
while ! nc -z postgres 5432; do
    sleep 0.1
done
echo "Database started"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start application with proper reload settings
echo "Starting application..."
if [ "$MODE" = "dev" ]; then
    echo "Running in development mode with reload enabled"
    exec python -m src.main
else
    echo "Running in production mode"
    exec python -m src.main
fi 