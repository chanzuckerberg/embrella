## Umbrella development helpers

# Use .env file
set dotenv-load

[private]
default:
  just --list --unsorted


# Echo useful info about current state of code/environment
info:
    #!/bin/bash
    source ./helpers/shell_common.sh
    echo -e "${GREEN}Project Info${NC}:"
    echo "Env: $DJANGO_ENV"
    # env present/env name
    # git remote/branch/repo state
    # git user/email
    # has gh cli?
    # has ssh access to umbrella?
    # os/uname of this machine
    # machine stats: cpus, ram, hd space remaining
    # public ip of this machine
    # ports open on this machine
    # prodserve running?
    # if prod, last db backup?
    echo ""

#############################################
# Dev environment setup/updating
#############################################

# Update conda environment from yml file
condasync:
    #!/bin/bash
    # if [ ! conda env list | grep -q "umbrella" ]; then conda env create -f environment.yml fi
    mamba env update --name umbrella --file environment.yml --prune

#############################################
# Environment Variable Helpers
#############################################

# Symmetric encrypt a file, asks for password.
[private]
encrypt +args="./.env":
    #!/bin/bash
    source ./helpers/shell_common.sh

    read -s -p "Password for encrypt: " password < /dev/tty
    #VK=$password openssl enc -aes-256-cbc -pbkdf2 -a -in ./.env -pass env:VK | VK=$password openssl enc -d -aes-256-cbc -pbkdf2 -a -in /dev/stdin -pass env:VK
    encrypt_file $password {{args}}

# Symmetric decrypt contents of stdin, asks for password.
[private]
decrypt:
    #!/bin/bash
    source ./helpers/shell_common.sh

    encrypted=$(</dev/stdin)
    read -s -p "Password for decrypt: " password < /dev/tty
    echo $encrypted | decrypt_stdin "$password"

# Checks that env exists, or initializes it from a template
initenv:
    #!/bin/bash
    source ./helpers/shell_common.sh
    mkdir -p ./.scratch

    if [ ! -f ".env" ]; then
      echo "No environment file setup. Making one from a template."
      echo -e "${RED}FILL OUT THIS FILE:${NC} ./.env"
      cp ./helpers/.env_template ./.env
      echo ""
    else
      if [ ! -z "${YOUDIDNOTUPDATETHIS:-}" ]; then
        echo -e "${RED}You need to fill out the environment variable file:${NC} ./.env"
        exit 1
      fi
      echo -e "${GREEN}Using environment variable file:${NC} ./.env"
    fi

# Uses github cli to fetch the environment file .env cached in encrypted form as a github variable, for a particular deployment environment: development, staging, production. Asks for password.
restoreencryptedenv +args="development":
    #!/bin/bash
    source ./helpers/shell_common.sh

    echocolor $RED "You are about to overwrite the local file ./.env with contents from remote environment for {{args}}..."
    if [[ "yes" == $(ask_if_really_sure) ]]
    then
      gh variable get ENV --repo czimaginginstitute/czii-umbrella-django --env {{args}} | just decrypt > ./.env
    fi

# Uses the github cli to fetch the service user credential. Asks for password.
getserviceuserkey +kf="~/.ssh/svc_czii_umbrella":
    #!/bin/bash
    source ./helpers/shell_common.sh
    echo "Getting service user key"
    k=$(gh variable get SVCUSR --repo czimaginginstitute/czii-umbrella-django --env production)
    echo $k | just decrypt > {{kf}}
    chmod 600 {{kf}}
    ssh-add {{kf}}

[private]
storeserviceuserkey +kf="~/.ssh/svc_czii_umbrella":
    #!/bin/bash
    source ./helpers/shell_common.sh
    k=$(just encrypt {{kf}})
    echo $k | gh variable set SVCUSR --repo czimaginginstitute/czii-umbrella-django --env production
    echo "Stored."

# Uses github cli to store encrypted file .env to github variable for particular deployment environment. Asks for password.
backupencryptedenv +args="development":
    #!/bin/bash
    source ./helpers/shell_common.sh

    echocolor $RED "You are about to overwrite the remote environment for {{args}} with the contents of ./.env..."
    if [[ "yes" == $(ask_if_really_sure) ]]
    then
      just encrypt ./.env | gh variable set ENV --repo czimaginginstitute/czii-umbrella-django --env {{args}}
    fi

# Get/install backend development lib dependencies
updatebackenddeps: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    echo -e "${GREEN}Getting git submodules...${NC}"
    git submodule update --init --recursive

    uv sync --locked
    echo -e "${GREEN}Done.${NC}"

# Get/install frontend development lib dependencies
updatefrontenddeps: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    if ! command -v yarn &>/dev/null; then
      echo "Yarn not found, installing..."
      npm install --global yarn
    else
      echo "Yarn is installed:" $(yarn --version)
    fi

    if ! command -v pm2 &>/dev/null; then
      echo "pm2 not found, installing..."
      npm install --global pm2
    else
      echo "pm2 is installed:" $(pm2 --version)
    fi

    # Run yarn install if file contents changed
    if [[ "yes" == $(check_filechanged ./frontend/package.json) ]]
    then
      echo -e "${GREEN}Installing packages with yarn...${NC}"
      pushd ./frontend
      set -x
      yarn install
      npm run bootstrap:submodule
      popd
      set +x
      set_filechanged ./frontend/package.json
    else
       echocolor $GREEN "Node package.json hasn't changed, skipping..."
    fi

# Run django manage.py {{args}} with environment variables set.
manage +args="": initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    export_env && uv run ./umbrella/manage.py {{args}}

yarn +args="": initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    pushd ./frontend
    yarn {{args}}
    popd

uv +args="": initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    export_env && uv {{args}}

# Run scripts to populate initial data during development
populatedbexamples: initenv
    #!/bin/bash
    export_env
    pushd ./umbrella
    set -x
    uv run ./manage.py runscript 001_init
    uv run ./manage.py runscript 002_permission
    uv run ./manage.py runscript 003_init_multigrid
    uv run ./manage.py runscript 004_init_processes
    uv run ./manage.py runscript 005_init_pytom_pick
    uv run ./manage.py runscript 006_init_copick_octopioctopi
    popd

#############################################
# Server run helpers
#############################################

# Run yarn dev in frontend with environment variables set
frontenddev: initenv
    #!/bin/bash
    pushd frontend
    yarn dev
    popd

# Run django runserver with environment variables set
backenddev: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    export_env
    just manage runserver

# Run both frontend and backend servers with environment variables set
servedev: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    uv run mkdocs build
    just manage migrate
    just backenddev &
    just frontenddev &
    wait $(jobs -p)


#############################################
# Documentation Helpers
#############################################

# Serves development server for viewing docs on port 8000 with live-reload.
servedocs +args="":
    #!/bin/bash
    uv run mkdocs serve --livereload --watch ./ {{args}}

# Build documents into docs_build/
builddocs:
    #!/bin/bash
    uv run mkdocs build

#############################################
# Deployment Helpers
#############################################

# Backs up mysql db to /srv/dbbackups on passed host (default: umbrella). Assumes ssh access as svc.czii.umbrella to host, and that MYSQL_USER and MYSQL_PASSWORD are in .env.
backupdb +host="umbrella":
    #!/bin/bash
    set -euo pipefail
    cat ./.env | grep MYSQL > ./.scratch/.dbenv
    ssh svc.czii.umbrella@{{host}} "mkdir -p /srv/dbbackups"
    scp ./.scratch/.dbenv svc.czii.umbrella@{{host}}:/srv/dbbackups/.dbenv
    ssh svc.czii.umbrella@{{host}} "chmod 600 /srv/dbbackups/.dbenv"
    echo "Backup up all databases on {{host}}... to /srv/dbbackups/..."
    ssh svc.czii.umbrella@{{host}} 'export $(cat /srv/dbbackups/.dbenv | xargs) && mysqldump -u $MYSQL_USER --all-databases --verbose > /srv/dbbackups/backup_$(date +%F.%H%M%S).sql'
    echo "Done. Backups:"
    ssh svc.czii.umbrella@{{host}} "rm /srv/dbbackups/.dbenv && ls -alh /srv/dbbackups/backup_*.sql"

mirrorproddbtostaging: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    LATEST=$(ssh svc.czii.umbrella@umbrella "cd /srv/dbbackups && ls -t backup_*.sql | head -n 1")
    scp svc.czii.umbrella@umbrella:/srv/dbbackups/$LATEST svc.czii.umbrella@umbrella-dev:/srv/$LATEST
    cat ./.env.staging | grep MYSQL > ./.scratch/.dbenv
    scp ./.scratch/.dbenv svc.czii.umbrella@umbrella-dev:/srv/dbbackups/.dbenv

    echo "Importing database from snapshot $LATEST..."
    mysql_cli='export $(cat /srv/dbbackups/.dbenv | xargs) && mysql -u umbrella'
    ssh svc.czii.umbrella@umbrella-dev "$mysql_cli < /srv/$LATEST"

mirrorproddbtolocal: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    LATEST=$(ssh svc.czii.umbrella@umbrella "cd /srv/dbbackups && ls -t backup_*.sql | head -n 1")
    scp svc.czii.umbrella@umbrella:/srv/dbbackups/$LATEST ./.scratch/$LATEST

    echo "Importing database from snapshot $LATEST..."
    mysql -h 127.0.0.1 -u root -p < ./.scratch/$LATEST

# Stop production server apps
stopprodserve: initenv
    #!/bin/bash
    set -euo pipefail

    # Stop backend gunicorn if it's running
    if [ -f ./logs/gunicorn_instance.pid ]; then
      pidtokill=$(<./logs/gunicorn_instance.pid)
      if kill -0 "$pidtokill" &> /dev/null; then
        echo "Killing running instance of gunicorn (pid $pidtokill)..."
        kill -15 $pidtokill
      else
        echo "Process $pidtokill from gunicorn_instance.pid no longer running"
      fi
      rm ./logs/gunicorn_instance.pid
    fi
    # If there are zombies kill them
    if ps aux | grep -v grep | grep "gunicorn_instance.pid --daemon" > /dev/null; then
      kill $(ps aux | grep "gunicorn_instance.pid --daemon" | grep -v grep | awk '{print $2}')
    fi

    # Stop frontend server with pm2 if it's running
    pm2pid=$(pm2 pid "my-app")
    if [ ! "" == $pm2pid ]; then
        echo "Frontend server running in pm2, pid: $pm2pid. Stopping it..."
        pm2 delete "my-app"
    fi

# (Re)start production server apps
startprodserve: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    set -euo pipefail
    just info

    # Stop running servers if they're running
    just stopprodserve

    echo "Starting gunicorn..."
    export_env && uv run gunicorn --bind 127.0.0.1 --name umbrella umbrella.wsgi:application --chdir ./umbrella --access-logfile ../logs/access.log --error-logfile ../logs/error.log --pid ../logs/gunicorn_instance.pid --daemon

    echo "Starting frontend server with pm2..."
    pushd ./frontend
    pm2 start npm --name "my-app" -- start
    popd

deploy stage envfile branch:
    #!/bin/bash
    source ./helpers/shell_common.sh

    echocolor $GREEN "You are about to deploy to {{stage}}, using the environment file: {{envfile}}, the branch: {{branch}}."
    if [[ "no" == $(ask_if_really_sure) ]]
    then
        echocolor $RED "Aborting."
      exit 0
    fi

    if [[ "{{stage}}" != "production" && "{{stage}}" != "staging" ]]; then
        echocolor $RED "Error: stage must be one of: staging, production"
        exit 1
    fi

    HOST=umbrella-dev
    CONF=./helpers/nginx_staging.conf
    if [[ "{{stage}}" == "production" ]]; then
        HOST=umbrella
        CONF=./helpers/nginx_production.conf
    fi

    # Git pull on host (or scp/rsync from here?)
    echocolor $GREEN "Pulling branch {{branch}}"
    scp ~/.ssh/svc_czii_umbrella svc.czii.umbrella@$HOST:~/.ssh/svc_czii_umbrella
    ssh svc.czii.umbrella@$HOST "chmod 600 ~/.ssh/svc_czii_umbrella && export GIT_SSH_COMMAND='ssh -i ~/.ssh/umbrella_deployment -o IdentitiesOnly=yes' && cd /srv && rm -rf czii-umbrella-django && git clone --depth 1 git@github.com:czimaginginstitute/czii-umbrella-django.git -b {{branch}}"

    echo "Copying .env to $HOST..."
    scp {{envfile}} svc.czii.umbrella@$HOST:/srv/czii-umbrella-django/.env

    # Transfer nginx conf
    echocolor $GREEN "Copying nginx conf $CONF to $HOST..."
    scp $CONF svc.czii.umbrella@$HOST:/etc/nginx/nginx.conf

    # Backup db
    if [[ "{{stage}}" == "production" ]]; then
      just backupdb
    else
      just mirrorproddbtostaging
    fi

    echocolor $GREEN "Checking if conda env exists already"
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && if conda info --envs | grep -q "^umbrella"; then echo "Conda env umbrella already exists"; else conda env create -f environment.yml; fi'

    echocolor $GREEN "Syncing conda env"
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && export MAMBA_NO_LOW_SPEED_LIMIT=1 && conda activate umbrella && time just condasync'


    echocolor $GREEN "Updating backend dependencies"
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && conda activate umbrella && time just updatebackenddeps'

    echocolor $GREEN "Updating frontend dependencies"
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && conda activate umbrella && time just updatefrontenddeps'

    # Build MkDocs documentation
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && conda activate umbrella && time just builddocs'

    echocolor $GREEN "Running any migrations..."
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && conda activate umbrella && just manage migrate'

    echocolor $GREEN "(Re)starting servers..."
    ssh svc.czii.umbrella@$HOST 'cd /srv/czii-umbrella-django && conda activate umbrella && just startprodserve && sleep 1 && systemctl restart nginx'

    echocolor $GREEN "Done."