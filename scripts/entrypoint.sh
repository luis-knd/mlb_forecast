#!/bin/bash

# Entrypoint script for the MLB Forecast application
# This script runs database migrations before starting the application

set -e

echo "🚀 Starting MLB Forecast Backend..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
while ! pg_isready -h postgres -p 5432 -U mlb_user; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "✅ PostgreSQL is ready!"

# Run database migrations
echo "📊 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi

# Start the application
echo "🎯 Starting the application..."
exec "$@"
