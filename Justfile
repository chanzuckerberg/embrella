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

# Run scripts to populate initial data during development.
# Pass a script name or path to run just that one, e.g.
#   just populatedbexamples 007_init_people
#   just populatedbexamples umbrella/scripts/007_init_people.py
populatedbexamples script="": initenv
    #!/bin/bash
    export_env
    pushd ./umbrella
    set -x
    if [ -n "{{script}}" ]; then
        # Accept a bare name or a path; runscript wants the module name only.
        name="$(basename "{{script}}")"; name="${name%.py}"
        uv run ./manage.py runscript "$name"
    else
        uv run ./manage.py runscript 001_init
        uv run ./manage.py runscript 002_permission
        uv run ./manage.py runscript 003_init_multigrid
        uv run ./manage.py runscript 004_init_processes
        uv run ./manage.py runscript 005_init_pytom_pick
        uv run ./manage.py runscript 007_init_people
    fi
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

# Backs up mysql db to /srv/dbbackups on passed host (default: umbrella). Assumes ssh access as svc.czii.umbrella to host, and that MYSQL_USER, MYSQL_PASSWORD, and MYSQL_NAME are in .env.
# Dumps ONLY the application database ($MYSQL_NAME), not the mysql system DB, preventing access issues when restoring.
backupdb envfile +host="umbrella" :
    #!/bin/bash
    set -euo pipefail
    cat {{envfile}} | grep MYSQL > ./.scratch/.dbenv
    ssh svc.czii.umbrella@{{host}} "mkdir -p /srv/dbbackups"
    scp ./.scratch/.dbenv svc.czii.umbrella@{{host}}:/srv/dbbackups/.dbenv
    ssh svc.czii.umbrella@{{host}} "chmod 600 /srv/dbbackups/.dbenv"
    echo 'Backing up application db ($MYSQL_NAME) on {{host}}... to /srv/dbbackups/...'
    ssh svc.czii.umbrella@{{host}} 'export $(cat /srv/dbbackups/.dbenv | xargs) && mysqldump -u $MYSQL_USER --databases "$MYSQL_NAME" --add-drop-database --verbose > /srv/dbbackups/backup_$(date +%F.%H%M%S).sql'
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

# Fetch the latest prod DB snapshot from umbrella:/srv/dbbackups into ./.scratch/.
# Host-side only (needs SSH access to umbrella). Pair with `just loaddevdb` to
# import into the dev compose db.
# Usage:
#   just fetchprodsnapshot              # from umbrella (production)
#   just fetchprodsnapshot umbrella-dev # from staging
fetchprodsnapshot host="umbrella": initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    set -euo pipefail

    LATEST=$(ssh svc.czii.umbrella@{{host}} "ls -t /srv/dbbackups/backup_*.sql | head -n 1 | xargs basename")
    echo "Fetching {{host}}:/srv/dbbackups/$LATEST → ./.scratch/$LATEST..."
    scp svc.czii.umbrella@{{host}}:/srv/dbbackups/$LATEST ./.scratch/$LATEST

    echocolor $GREEN "Fetched ./.scratch/$LATEST"
    echo "Next: just devexec just loaddevdb ./.scratch/$LATEST    # (or just loaddevdb ./.scratch/$LATEST from host)"

# Load a SQL snapshot into the dev compose `db` service.
# `snapshot` is a path to the .sql file (relative or absolute).
# Usage:
#   just loaddevdb ./.scratch/backup_2026-05-17.123456.sql       # host
#   just devexec just loaddevdb ./.scratch/backup_…sql           # devcontainer
loaddevdb snapshot: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    set -euo pipefail

    if [ ! -f "{{snapshot}}" ]; then
      echocolor $RED "Snapshot not found: {{snapshot}}"
      exit 1
    fi

    DB_TARGET="${MYSQL_HOST:-127.0.0.1} (dev compose db)"
    echocolor $GREEN "Target: $DB_TARGET"

    # --skip-ssl: dev db container has no TLS configured; recent MariaDB/MySQL
    # clients require it by default and bail with "SSL is required".
    echo "Importing {{snapshot}} into dev db..."
    mysql --skip-ssl -h "${MYSQL_HOST:-127.0.0.1}" -u root -pdevaccount < "{{snapshot}}"

    echocolor $GREEN "Loaded {{snapshot}} into dev db at $DB_TARGET."

# Back up the dev compose db to ./.scratch/ (the dump pair of `loaddevdb`). Mirrors
# loaddevdb: connects to ${MYSQL_HOST:-127.0.0.1} with the MariaDB client, so it runs
# inside the devcontainer (MYSQL_HOST=db) or on the host with the dev stack up. The
# -h connection authenticates as root@'%' (devaccount), created by the db container init.
# Usage:
#   just devexec just dbbackupdev            # devcontainer
#   just dbbackupdev                         # host (dev stack up)
#   just loaddevdb ./.scratch/devbackup_<ts>.sql   # to restore it back
dbbackupdev: initenv
    #!/bin/bash
    source ./helpers/shell_common.sh
    set -euo pipefail
    mkdir -p ./.scratch
    OUT="./.scratch/devbackup_$(date +%F.%H%M%S).sql"
    echo "Backing up dev compose db (application DB only) → $OUT ..."
    mysqldump --skip-ssl -h "${MYSQL_HOST:-127.0.0.1}" -u root -pdevaccount \
      --databases "${MYSQL_NAME:-umbrella}" --add-drop-database > "$OUT"
    echocolor $GREEN "Wrote $OUT"

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

    # NOTE: this bare-metal recipe (host system nginx) is superseded by the
    # container deploy `deployv2`, which instead uses the nginx_*.conf.template
    # variants mounted into the nginx container.
    HOST=umbrella-dev
    CONF=./infra/nginx_staging.conf
    if [[ "{{stage}}" == "production" ]]; then
        HOST=umbrella
        CONF=./infra/nginx_production.conf
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


# ─────────────────────────────────────────────────────────────────────────────
# Container workflows — recipes below run the containerized dev/staging/prod
# stacks via podman compose. Does not include Docker commands yet.
# ─────────────────────────────────────────────────────────────────────────────

# Compose invocation pattern. `--env-file .env` makes ${VAR:-default} substitutions
# in compose.yaml resolve against the repo-root .env (Compose's default lookup
# would search next to the compose file, which is in infra/ and has no .env).
COMPOSE_DEV := "podman compose --env-file .env -f infra/compose.yaml -f infra/compose.build.yaml -f infra/compose.dev.yaml"

# One-time setup: create the shared external `embrella` podman network. Idempotent.
netinit:
    @podman network inspect embrella >/dev/null 2>&1 || podman network create embrella

# Bring up the dev stack (db, backend, worker, frontend, nginx) in the background.
# First run builds images; subsequent runs use cached layers.
devup: netinit
    {{COMPOSE_DEV}} up -d --build

# Tear the dev stack down. Named volumes (db_data, frontend_node_modules, etc.) survive.
devdown:
    {{COMPOSE_DEV}} down

# Tail logs from all dev services, or a specific one (e.g. `just devlogs backend`).
devlogs service="":
    {{COMPOSE_DEV}} logs -f {{service}}

# Run a one-off command inside the running backend container.
# Example: `just devexec pytest umbrella/processes/tests/test_services.py`
devexec +args:
    {{COMPOSE_DEV}} exec backend {{args}}

# Drop into an interactive zsh shell in the dev container as the embrella user.
devshell:
    {{COMPOSE_DEV}} exec -it -u embrella backend zsh -l

# Build backend + frontend images with the given tag (e.g. `just buildimages staging`).
buildimages tag:
    podman build -f infra/backend.Dockerfile  -t embrella/backend:{{tag}}  .
    podman build -f infra/frontend.Dockerfile -t embrella/frontend:{{tag}} .

# Container-based deploy (parallel to the bare-metal `deploy` recipe).
# `stage` is the overlay token (prod|staging → infra/compose.<stage>.yaml);
# `envfile` is the local env file copied to the host as .env.<production|staging>
# (read by the overlay's env_file and compose's --env-file); `branch` is the git
# ref the host is checked out to (deterministically, via fetch + reset --hard);
# `tag` is the image tag (defaults to `latest`).
# Examples:
#   just deployv2 staging .env.staging main                  # tag defaults to latest
#   just deployv2 prod    .env.production v1.2.3-branch v1.2.3
# Prereq on the target host (one-time): `podman network create embrella`, plus
# place the SLURM SSH key (from vault/admin) on the host and point the env file's
# SLURM_KEYFILE at that host path (it's bind-mounted into the containers).
#
# The db's data persists in the `db_data` named volume across redeploys.
# A fresh host boots a working *empty* app DB on its own
# use `just loadcontainerdb` to seed. Back up on demand with `just dbbackupv2`.
deployv2 stage envfile branch tag="latest":
    #!/bin/bash
    set -euo pipefail
    if [[ "{{stage}}" != "prod" && "{{stage}}" != "staging" ]]; then
        echo "Error: stage must be one of: prod, staging"; exit 1
    fi
    HOST=umbrella-dev; ENVNAME=staging
    if [[ "{{stage}}" == "prod" ]]; then HOST=umbrella; ENVNAME=production; fi
    # Snapshot the currently-running db before switching containers. Best-effort:
    # a fresh host (no .env.<name> / no running db yet) shouldn't block the deploy.
    echo "Backing up the current {{stage}} db before the switch..."
    just dbbackupv2 {{stage}} || echo "  ⚠ pre-deploy backup skipped/failed (fresh host or db down) — continuing."
    echo "Copying {{envfile}} to $HOST:/srv/czii-umbrella-django/.env.$ENVNAME ..."
    scp {{envfile}} svc.czii.umbrella@$HOST:/srv/czii-umbrella-django/.env.$ENVNAME
    echo "Checking the SLURM key exists on $HOST..."
    ssh svc.czii.umbrella@$HOST "set -euo pipefail; cd /srv/czii-umbrella-django; \
      KEY=\$(grep -E '^SLURM_KEYFILE=' .env.$ENVNAME | tail -1 | cut -d= -f2- | tr -d '\"' | tr -d \"'\"); \
      if [[ -z \"\$KEY\" ]]; then echo \"  ✗ SLURM_KEYFILE not set in .env.$ENVNAME\"; exit 1; fi; \
      if [[ ! -f \"\$KEY\" ]]; then echo \"  ✗ SLURM key not found at \$KEY (obtain it from an admin/vault and place it there)\"; exit 1; fi; \
      echo \"  ✓ found at \$KEY\""
    echo "Checking out branch {{branch}} on $HOST and pulling prebuilt images from ghcr.io..."
    # Images are built/pushed by .github/workflows/build-images.yaml to
    # ghcr.io/czimaginginstitute/embrella/{backend,frontend,db}. The host still
    # needs the source checked out for infra/compose*.yaml + nginx templates.
    # TODO: get self-hosted runner set up to automate all of this, including the templates.
    ssh svc.czii.umbrella@$HOST "set -e; cd /srv/czii-umbrella-django && \
      export GIT_SSH_COMMAND='ssh -i ~/.ssh/umbrella_deployment -o IdentitiesOnly=yes' && \
      git fetch origin {{branch}} && git checkout -B {{branch}} FETCH_HEAD && \
      (podman network inspect embrella >/dev/null 2>&1 || podman network create embrella) && \
      GHCR_USER=\$(grep -E '^GHCR_USER=' .env.$ENVNAME | tail -1 | cut -d= -f2- | tr -d '\"' | tr -d \"'\"); \
      GHCR_TOKEN=\$(grep -E '^GHCR_TOKEN=' .env.$ENVNAME | tail -1 | cut -d= -f2- | tr -d '\"' | tr -d \"'\"); \
      if [[ -z \"\$GHCR_USER\" || -z \"\$GHCR_TOKEN\" ]]; then echo '  ✗ GHCR_USER/GHCR_TOKEN not set in .env.$ENVNAME (need a PAT with read:packages)'; exit 1; fi; \
      echo \"\$GHCR_TOKEN\" | podman login ghcr.io -u \"\$GHCR_USER\" --password-stdin && \
      export IMAGE_REGISTRY=ghcr.io/czimaginginstitute/embrella IMAGE_TAG={{tag}} && \
      podman compose --env-file .env.$ENVNAME -f infra/compose.yaml -f infra/compose.{{stage}}.yaml pull && \
      podman compose --env-file .env.$ENVNAME -f infra/compose.yaml -f infra/compose.{{stage}}.yaml up -d --remove-orphans"

# Restore a specific SQL snapshot into the prod/staging *container* db, then apply
# migrations. Use to load real data: disaster recovery, seeding a fresh host, or
# rollback. Runs on the target host via SSH; the dump must already be at
# /srv/dbbackups/<snapshot> there (where `dbbackupv2` writes it), and the host's
# .env.<production|staging> (placed by deployv2) supplies the db root password.
#
# After restoring, this runs the one-shot `migrate` service so a snapshot that
# predates the deployed code is brought up to the current schema (the migrate
# service owns the stores → projects → rest ordering; see entrypoint-backend.sh).
#
# CAUTION: a legacy `--all-databases` dump (what bare-metal `backupdb` produces) DOES
# include the mysql system DB and can clobber the container's grants — if you restore
# one of those, afterwards verify root-from-% access and app-user grants still work.
#
# Usage:
#   just loadcontainerdb staging backup_2026-05-17.123456.sql
#   just loadcontainerdb prod    backup_2026-05-17.123456.sql
loadcontainerdb stage snapshot:
    #!/bin/bash
    set -euo pipefail
    if [[ "{{stage}}" != "prod" && "{{stage}}" != "staging" ]]; then
        echo "Error: stage must be one of: prod, staging"; exit 1
    fi
    HOST=umbrella-dev; ENVNAME=staging
    if [[ "{{stage}}" == "prod" ]]; then HOST=umbrella; ENVNAME=production; fi
    echo "Loading /srv/dbbackups/{{snapshot}} into the {{stage}} db container on $HOST, then migrating..."
    ssh svc.czii.umbrella@$HOST "set -euo pipefail; \
      cd /srv/czii-umbrella-django && \
      export \$(grep '^MYSQL' .env.$ENVNAME | xargs) && \
      podman compose --env-file .env.$ENVNAME -f infra/compose.yaml -f infra/compose.{{stage}}.yaml \
        exec -T db mariadb --skip-ssl -h127.0.0.1 --protocol=tcp -uroot -p\"\$MYSQL_PWD\" < /srv/dbbackups/{{snapshot}} && \
      echo 'Restore complete; applying migrations to the restored db...' && \
      podman compose --env-file .env.$ENVNAME -f infra/compose.yaml -f infra/compose.{{stage}}.yaml run --rm migrate"
    echo "Done. (If you restored a legacy --all-databases dump, verify root-from-% access and app-user grants.)"

# On-demand backup of the *containerized* db for a stage's stack. Dumps ONLY the
# application database ($MYSQL_NAME) to
# /srv/dbbackups/backup_<ts>.sql on the stack's host (same location/format as legacy
# `backupdb`, so `loadcontainerdb`, `fetchprodsnapshot`, and `loaddevdb` all consume it).
#
# Usage:
#   just dbbackupv2 prod
#   just dbbackupv2 staging
dbbackupv2 stage:
    #!/bin/bash
    set -euo pipefail
    if [[ "{{stage}}" != "prod" && "{{stage}}" != "staging" ]]; then
        echo "Error: stage must be one of: prod, staging"; exit 1
    fi
    HOST=umbrella-dev; ENVNAME=staging
    if [[ "{{stage}}" == "prod" ]]; then HOST=umbrella; ENVNAME=production; fi
    echo "Backing up the {{stage}} container db (application DB only) on $HOST → /srv/dbbackups/ ..."
    # Dump to a hidden .partial first and rename only on success
    ssh svc.czii.umbrella@$HOST "set -euo pipefail; \
      cd /srv/czii-umbrella-django && \
      mkdir -p /srv/dbbackups && \
      export \$(grep '^MYSQL' .env.$ENVNAME | xargs) && \
      TS=\$(date +%F.%H%M%S) && \
      podman compose --env-file .env.$ENVNAME -f infra/compose.yaml -f infra/compose.{{stage}}.yaml \
        exec -T db mariadb-dump --skip-ssl -h127.0.0.1 --protocol=tcp -uroot -p\"\$MYSQL_PWD\" --databases \"\$MYSQL_NAME\" --add-drop-database \
        > /srv/dbbackups/.backup_\$TS.sql.partial && \
      mv /srv/dbbackups/.backup_\$TS.sql.partial /srv/dbbackups/backup_\$TS.sql"
    echo "Done. Latest backups on $HOST:"
    ssh svc.czii.umbrella@$HOST "ls -alh /srv/dbbackups/backup_*.sql | tail -n 5"
