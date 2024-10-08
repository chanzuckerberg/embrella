#!/bin/bash

# Load environment variables from .env file
if [ -f "env" ]; then
  echo "Loading environment variables from env file..."
  while IFS='=' read -r key value; do
    export "$key"="$value"
  done < env
  echo "Environment variables loaded successfully."
else
  echo "env file not found."
  exit 1
fi