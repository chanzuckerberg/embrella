#!/bin/bash

# Load environment variables from .env file
if [ -f env ]; then
    export $(grep -v '^#' env | xargs)
    echo "Environment variables loaded from env file."
else
    echo "env file not found!"
fi