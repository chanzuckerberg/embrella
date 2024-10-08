#!/bin/bash

# Load environment variables from env file
export $(grep -v '^#' env | xargs)

# Print confirmation message
echo "Environment variables have been successfully loaded from .env"

