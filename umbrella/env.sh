
#!/bin/bash

# Load environment variables from env file
if [ -f "env" ]; then
  echo "Loading environment variables from env file..."
  while IFS= read -r line; do
    line=${line##export }
    if [ -n "$line" ]; then
      key=${line%%=*}
      value=${line#*=}
      value=${value//\'/} # Remove single quotes
      export "$key"="$value"
    fi
  done < env
  echo "Environment variables loaded successfully."
else
  echo "env file not found."
  exit 1
fi