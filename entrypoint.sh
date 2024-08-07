#!/bin/bash
# entrypoint.sh

# Install netcat if it's not already installed
if ! command -v nc >/dev/null 2>&1; then
    echo "Installing netcat..."
    apt-get update && apt-get install -y netcat
fi

# Wait for PostgreSQL to be ready (you may need to adjust this depending on your setup)
echo "Waiting for PostgreSQL to be ready..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done

# Apply database migrations
echo "Applying database migrations..."
python3 manage.py makemigrations
python3 manage.py migrate

# Collect static files (optional, if you're serving static files)
echo "Collecting static files..."
python3 manage.py collectstatic --noinput

# Start the server
echo "Starting server..."
exec "$@"
