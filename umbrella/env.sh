#!/bin/bash

# Load environment variables from .env file
if [ -f ".env" ]; then
  echo "Loading environment variables from env file..."
  export $(grep -v '^#' env | xargs -d '\n')
  echo "Environment variables loaded successfully."
else
  echo ".env file not found."
  exit 1
fi