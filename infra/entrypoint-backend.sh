#!/bin/sh
# Backend container entrypoint. Runs in every backend AND worker container start.
#
# Environment variables read:
#   USE_MYSQL              "True" to wait for MYSQL_HOST:MYSQL_PORT before starting Django.
#   MYSQL_HOST/USER/PWD/NAME/PORT   DB connection used for the wait probe.
#   EMBRELLA_BUILD_STATIC  "1" → run collectstatic + mkdocs build before exec.
#                          Set on the gunicorn (web) container in staging/prod.
#                          Unset everywhere else: workers, dev runserver, etc.
#   EMBRELLA_MIGRATE       "1" → run DB migrations before exec. Set ONLY on the
#                          one-shot `migrate` service so backend + worker never
#                          race into migrate on a fresh DB.

set -e

if [ "$USE_MYSQL" = "True" ] && [ -n "$MYSQL_HOST" ]; then
  echo "Waiting for MySQL at $MYSQL_HOST:${MYSQL_PORT:-3306}..."
  i=0
  until python -c "import MySQLdb, os; MySQLdb.connect(host=os.environ['MYSQL_HOST'], user=os.environ['MYSQL_USER'], passwd=os.environ['MYSQL_PWD'], db=os.environ['MYSQL_NAME'], port=int(os.environ.get('MYSQL_PORT','3306')))" 2>/dev/null; do
    i=$((i+1))
    if [ "$i" -gt 60 ]; then
      echo "MySQL did not become reachable in time" >&2
      exit 1
    fi
    sleep 2
  done
  echo "MySQL reachable."
fi

# Migrations run only in the dedicated one-shot `migrate` service (EMBRELLA_MIGRATE=1)
# Migration ordering (stores → projects → rest)
if [ "$EMBRELLA_MIGRATE" = "1" ]; then
  echo "Running migrations..."
  python umbrella/manage.py migrate stores --noinput
  python umbrella/manage.py migrate projects --noinput
  python umbrella/manage.py migrate --noinput
  echo "Migrations complete."
fi

if [ "$EMBRELLA_BUILD_STATIC" = "1" ]; then
  echo "Collecting static files..."
  python umbrella/manage.py collectstatic --noinput
  echo "Building docs..."
  mkdocs build || echo "mkdocs build failed (non-fatal)"
  echo "Static files collected and docs built."
fi

exec "$@"
