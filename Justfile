# Umbrella development helpers

# Use .env file
set dotenv-load

[private]
default:
  just --list --unsorted


# Echo useful info about current state of code/environment
info:
    #!/bin/bash
    source ./helpers/shell_common.sh
    set +e  # Don't exit on errors for info gathering

    # Load environment variables if .env exists
    if [ -f ".env" ]; then
        export_env 2>/dev/null
    fi

    echo ""
    echocolor $GREEN "═══════════════════════════════════════════════════════"
    echocolor $GREEN "  Embrella Project Info"
    echocolor $GREEN "═══════════════════════════════════════════════════════"
    echo ""

    echocolor $GREEN "▸ Environment Configuration:"
    if [ -f ".env" ]; then
        echo "  😀 .env file: present"
        if [ ! -z "${DJANGO_ENV:-}" ]; then
            echo "  • Django environment: $DJANGO_ENV"
        else
            echo "  • Django environment: not set"
        fi
        if [ ! -z "${USE_MYSQL:-}" ]; then
            echo "  • Database: MySQL (USE_MYSQL=$USE_MYSQL)"
        else
            echo "  • Database: SQLite (default)"
        fi
    else
        echo "  🤮 .env file: missing (run 'just initenv')"
    fi

    if [ ! -z "${CONDA_DEFAULT_ENV:-}" ]; then
        echo "  😀 Conda environment: $CONDA_DEFAULT_ENV"
    else
        echo "  🤮 Conda environment: not activated"
    fi
    echo ""

    # Git Repository Status
    echocolor $GREEN "▸ Git Repository:"
    if git rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH=$(git branch --show-current)
        echo "  • Branch: $BRANCH"

        REMOTE=$(git remote get-url origin 2>/dev/null || echo "no remote")
        echo "  • Remote: $REMOTE"

        GIT_USER=$(git config user.name 2>/dev/null || echo "not set")
        GIT_EMAIL=$(git config user.email 2>/dev/null || echo "not set")
        echo "  • Git user: $GIT_USER <$GIT_EMAIL>"

        if git diff-index --quiet HEAD -- 2>/dev/null; then
            echo "  😀 Working tree: clean"
        else
            CHANGED=$(git status --porcelain | wc -l | xargs)
            echo "  • Working tree: $CHANGED files changed"
        fi

        echo "  • Recent commits:"
        git log --oneline -3 | sed 's/^/    /'
    else
        echo "  🤮 Not a git repository"
    fi
    echo ""

    echocolor $GREEN "▸ System Information:"
    echo "  • OS: $(uname -s) $(uname -r)"
    echo "  • Architecture: $(uname -m)"

    if command -v sysctl &>/dev/null; then
        CPUS=$(sysctl -n hw.ncpu 2>/dev/null || echo "unknown")
        echo "  • CPUs: $CPUS"
        MEM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024 ))
        if [ $MEM_GB -gt 0 ]; then
            echo "  • Memory: ${MEM_GB} GB"
        fi
    elif [ -f /proc/cpuinfo ]; then
        CPUS=$(grep -c ^processor /proc/cpuinfo)
        echo "  • CPUs: $CPUS"
        MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
        echo "  • Memory: ${MEM_GB} GB"
    fi

    DISK_USAGE=$(df -h . | awk 'NR==2 {print $5 " used, " $4 " available"}')
    echo "  • Disk: $DISK_USAGE"
    echo ""

    echocolor $GREEN "▸ Development Tools:"

    if command -v python &>/dev/null; then
        PYTHON_VER=$(python --version 2>&1 | cut -d' ' -f2)
        echo "  😀 Python: $PYTHON_VER"
    else
        echo "  🤮 Python: not found"
    fi

    if command -v node &>/dev/null; then
        NODE_VER=$(node --version)
        echo "  😀 Node.js: $NODE_VER"
    else
        echo "  🤮 Node.js: not found"
    fi

    if command -v yarn &>/dev/null; then
        YARN_VER=$(yarn --version)
        echo "  😀 Yarn: $YARN_VER"
    else
        echo "  🤮 Yarn: not installed"
    fi

    if command -v uv &>/dev/null; then
        UV_VER=$(uv --version | cut -d' ' -f2)
        echo "  😀 uv: $UV_VER"
    else
        echo "  🤮 uv: not found"
    fi

    if command -v gh &>/dev/null; then
        GH_VER=$(gh --version | head -n1 | cut -d' ' -f3)
        echo "  😀 GitHub CLI: $GH_VER"
    else
        echo "  🤮 GitHub CLI: not installed"
    fi

    if command -v pm2 &>/dev/null; then
        PM2_VER=$(pm2 --version)
        echo "  😀 pm2: $PM2_VER"
    else
        echo "  🤮 pm2: not installed"
    fi
    echo ""

    echocolor $GREEN "▸ SSH Access:"
    if ssh -o BatchMode=yes -o ConnectTimeout=3 svc.czii.umbrella@umbrella "exit" 2>/dev/null; then
        echo "  😀 umbrella (production): accessible"
    else
        echo "  🤮 umbrella (production): not accessible"
    fi

    if ssh -o BatchMode=yes -o ConnectTimeout=3 svc.czii.umbrella@umbrella-dev "exit" 2>/dev/null; then
        echo "  😀 umbrella-dev (staging): accessible"
    else
        echo "  🤮 umbrella-dev (staging): not accessible"
    fi

    # Check cluster access using SLURM credentials
    if [ ! -z "${SLURM_USER:-}" ] && [ ! -z "${SLURM_KEYFILE:-}" ]; then
        if [ -f "${SLURM_KEYFILE}" ]; then
            if ssh -o BatchMode=yes -o ConnectTimeout=3 -i ${SLURM_KEYFILE} ${SLURM_USER}@czii-login-1.czbiohub.org "exit" 2>/dev/null; then
                echo "  😀 czii cluster (czii-login-1.czbiohub.org): accessible as ${SLURM_USER}"
            else
                echo "  🤮 czii cluster (czii-login-1.czbiohub.org): not accessible as ${SLURM_USER}"
            fi

            if ssh -o BatchMode=yes -o ConnectTimeout=3 -i ${SLURM_KEYFILE} ${SLURM_USER}@login.bruno.czbiohub.org "exit" 2>/dev/null; then
                echo "  😀 bruno cluster (login.bruno.czbiohub.org): accessible as ${SLURM_USER}"
            else
                echo "  🤮 bruno cluster (login.bruno.czbiohub.org): not accessible as ${SLURM_USER}"
            fi
        else
            echo "  🤮 czii/bruno clusters: SLURM_KEYFILE not found at ${SLURM_KEYFILE}"
        fi
    else
        echo "  • czii/bruno clusters: SLURM_USER and SLURM_KEYFILE not configured"
    fi
    echo ""

    echocolor $GREEN "▸ Running Services:"

    # Check if qcluster is running
    if [ -f "./logs/qcluster.pid" ]; then
        QCLUSTER_PID=$(<./logs/qcluster.pid)
        if kill -0 "$QCLUSTER_PID" 2>/dev/null; then
            echo "  😀 qcluster (task processor): running (PID: $QCLUSTER_PID)"
        else
            echo "  🤮 qcluster (task processor): not running (stale PID file)"
        fi
    else
        echo "  • qcluster (task processor): not running"
    fi

    # Check if gunicorn is running
    if [ -f "./logs/gunicorn_instance.pid" ]; then
        GUNICORN_PID=$(<./logs/gunicorn_instance.pid)
        if kill -0 "$GUNICORN_PID" 2>/dev/null; then
            echo "  😀 Gunicorn (backend): running (PID: $GUNICORN_PID)"
        else
            echo "  🤮 Gunicorn (backend): not running (stale PID file)"
        fi
    else
        echo "  • Gunicorn (backend): not running"
    fi

    # Check if pm2 frontend is running
    if command -v pm2 &>/dev/null; then
        PM2_STATUS=$(pm2 pid "my-app" 2>/dev/null || echo "")
        if [ ! -z "$PM2_STATUS" ] && [ "$PM2_STATUS" != "0" ]; then
            echo "  😀 Next.js frontend (pm2): running (PID: $PM2_STATUS)"
        else
            echo "  • Next.js frontend (pm2): not running"
        fi
    fi

    # Check for dev servers
    if lsof -ti:8000 &>/dev/null; then
        DEV_PID=$(lsof -ti:8000)
        echo "  • Port 8000 (backend dev): in use (PID: $DEV_PID)"
    fi

    if lsof -ti:3000 &>/dev/null; then
        DEV_PID=$(lsof -ti:3000)
        echo "  • Port 3000 (frontend dev): in use (PID: $DEV_PID)"
    fi
    echo ""

    echocolor $GREEN "▸ Database Backups:"
    if ssh -o BatchMode=yes -o ConnectTimeout=3 svc.czii.umbrella@umbrella "ls -t /srv/dbbackups/backup_*.sql 2>/dev/null | head -n1" 2>/dev/null; then
        LATEST_BACKUP=$(ssh svc.czii.umbrella@umbrella "ls -t /srv/dbbackups/backup_*.sql 2>/dev/null | head -n1 | xargs basename")
        BACKUP_SIZE=$(ssh svc.czii.umbrella@umbrella "ls -lh /srv/dbbackups/backup_*.sql 2>/dev/null | head -n1 | awk '{print \$5}'")
        echo "  • Latest backup: $LATEST_BACKUP ($BACKUP_SIZE)"
    else
        echo "  • Unable to check backups (no SSH access)"
    fi
    echo ""

    # Django Migrations Status
    if [ -f ".env" ] && [ ! -z "${CONDA_DEFAULT_ENV:-}" ]; then
        echocolor $GREEN "▸ Django Migrations:"
        PENDING=$(uv run ./umbrella/manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l | xargs)
        if [ "$PENDING" -eq "0" ]; then
            echo "  😀 All migrations applied"
        else
            echo "  • Pending migrations: $PENDING (run 'just manage migrate')"
        fi
        echo ""
    fi

    echocolor $GREEN "═══════════════════════════════════════════════════════"
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

# Uses github cli to fetch the environment file .env cached in encrypted form as a github variable, for a particular deployment environment: development, staging, production. Asks for password.
restoreencryptedenv +args="development":
    #!/bin/bash
    source ./helpers/shell_common.sh

    echocolor $RED "You are about to overwrite the local file ./.env with contents from remote environment for {{args}}..."
    if [[ "yes" == $(ask_if_really_sure) ]]
    then
      k=$(gh variable get ENV --repo czimaginginstitute/czii-umbrella-django --env {{args}})
      echo $k | just decrypt > ./.env
    fi

# Uses github cli to store encrypted file .env to github variable for particular deployment environment. Asks for password.
backupencryptedenv +args="development":
    #!/bin/bash
    source ./helpers/shell_common.sh

    echocolor $RED "You are about to overwrite the remote environment for {{args}} with the contents of ./.env..."
    if [[ "yes" == $(ask_if_really_sure) ]]
    then
      k=$(just encrypt ./.env)
      echo $k | gh variable set ENV --repo czimaginginstitute/czii-umbrella-django --env {{args}}
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
      # npm run bootstrap:submodule
      yarn build
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
    just manage qcluster &
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
backupdb envfile +host="umbrella" :
    #!/bin/bash
    set -euo pipefail
    cat {{envfile}} | grep MYSQL > ./.scratch/.dbenv
    ssh svc.czii.umbrella@{{host}} "mkdir -p /srv/dbbackups"
    scp ./.scratch/.dbenv svc.czii.umbrella@{{host}}:/srv/dbbackups/.dbenv
    ssh svc.czii.umbrella@{{host}} "chmod 600 /srv/dbbackups/.dbenv"
    echo "Backup up all databases on {{host}}... to /srv/dbbackups/..."
    ssh svc.czii.umbrella@{{host}} 'export $(cat /srv/dbbackups/.dbenv | xargs) && mysqldump -u $MYSQL_USER --all-databases --add-drop-database --verbose > /srv/dbbackups/backup_$(date +%F.%H%M%S).sql'
    echo "Done. Backups:"
    ssh svc.czii.umbrella@{{host}} "rm /srv/dbbackups/.dbenv && ls -alh /srv/dbbackups/backup_*.sql"

mirrorproddbtostaging: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    LATEST=$(ssh svc.czii.umbrella@umbrella "cd /srv/dbbackups && ls -t backup_*.sql | head -n 1")
    # echo $LATEST
    scp svc.czii.umbrella@umbrella:/srv/dbbackups/$LATEST svc.czii.umbrella@umbrella-dev:/srv/dbbackups/$LATEST
    scp ./.scratch/.dbenv svc.czii.umbrella@umbrella-dev:/srv/dbbackups/.dbenv

    echo "Importing database from snapshot $LATEST..."
    mysql_cli='export $(cat /srv/dbbackups/.dbenv | xargs) && mysql -u umbrella'
    ssh svc.czii.umbrella@umbrella-dev "$mysql_cli < /srv/dbbackups/$LATEST"

mirrorproddbtolocal: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh

    LATEST=$(ssh svc.czii.umbrella@umbrella "cd /srv/dbbackups && ls -t backup_*.sql | head -n 1")
    scp svc.czii.umbrella@umbrella:/srv/dbbackups/$LATEST ./.scratch/$LATEST

    echo "Importing database from snapshot $LATEST..."
    mysql -h 127.0.0.1 -u root -pdevaccount < ./.scratch/$LATEST

    echo "Re-applying remote host grants..."
    mysql -h 127.0.0.1 -u root -pdevaccount < ./helpers/local_mysql/init.sql

# Stop production server apps
stopprodserve: initenv
    #!/bin/bash
    set -euo pipefail

    # Stop qcluster if it's running
    if [ -f ./logs/qcluster.pid ]; then
      pidtokill=$(<./logs/qcluster.pid)
      if kill -0 "$pidtokill" &> /dev/null; then
        echo "Killing running instance of qcluster (pid $pidtokill)..."
        kill -15 $pidtokill
      else
        echo "Process $pidtokill from qcluster.pid no longer running"
      fi
      rm ./logs/qcluster.pid
    fi
    # If there are zombie qcluster processes, kill them
    if ps aux | grep -v grep | grep "manage.py qcluster" > /dev/null; then
      echo "Killing zombie qcluster processes..."
      kill $(ps aux | grep "manage.py qcluster" | grep -v grep | awk '{print $2}') 2>/dev/null || true
    fi

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

    echo "Starting background task processor (qcluster)..."
    mkdir -p ./logs
    # Daemonize qcluster properly for SSH sessions
    export_env && nohup setsid uv run ./umbrella/manage.py qcluster >> ./logs/qcluster.log 2>&1 &
    sleep 1
    pgrep -f "manage.py qcluster" > ./logs/qcluster.pid || true
    echo "qcluster started with PID $(cat ./logs/qcluster.pid 2>/dev/null || echo 'unknown')"

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
      just backupdb {{envfile}}
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
