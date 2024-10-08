#!/bin/bash

# Define the path to the .env file
ENV_FILE="var.env"

# Check if the .env file exists
if [ -f "$ENV_FILE" ]; then
    # Load environment variables from the .env file
    export $(grep -v '^#' "$ENV_FILE" | xargs)
    echo "Environment variables loaded from $ENV_FILE."
else
    echo ".env file not found at $ENV_FILE!"
    exit 1
fi


# Check if gunicorn is running and kill the process
gunicorn_pid=$(ss -tulpn | grep gunicorn | awk '{print $7}' | cut -d'/' -f1)
if [ -n "$gunicorn_pid" ]; then
    echo "Stopping gunicorn process with PID: $gunicorn_pid"
    kill -15 "$gunicorn_pid"
    echo "Gunicorn stopped."
else
    echo "Gunicorn is not running."
fi

# Start gunicorn with specified parameters
gunicorn --bind 127.0.0.1 umbrella.wsgi:application --daemon --access-logfile access.log --error-logfile error.log

echo "Gunicorn started."