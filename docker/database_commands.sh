#!/usr/bin/env bash
# Back up and restore the Embrella database. Run beside docker-compose.yml.
#
#   ./database_commands.sh backup            -> backups/embrella_<timestamp>.sql.gz
#   ./database_commands.sh restore <file>    -> replaces the database with <file> (.sql.gz or .sql)
#
# Uses 'docker compose' if available, else 'podman compose'. Override with
# COMPOSE="podman compose" ./database_commands.sh backup

set -euo pipefail

readonly BACKUP_DIR=backups
readonly DUMP_MARKER='^-- Dump completed'
readonly DB_WAIT_SECONDS=120

cd "$(dirname "$0")"

if [ -z "${COMPOSE:-}" ]; then
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
  else
    COMPOSE="podman compose"
  fi
fi

compose() {
  $COMPOSE "$@"
}

die() {
  echo "error: $*" >&2
  exit 1
}

# Print a dump, decompressing .gz. Picks by extension, not gzip -f, for BSD/GNU parity.
cat_dump() {
  case "$1" in
    *.gz) gunzip -c "$1" ;;
    *) cat "$1" ;;
  esac
}

# mariadb-dump writes the marker last, so its absence means a failed or cut-off dump.
is_complete() {
  cat_dump "$1" 2>/dev/null | tail -n 1 | grep -q "$DUMP_MARKER"
}

# TCP ping: the image's first-boot init server is socket-only, so this waits for the real one.
wait_for_db() {
  local i
  for ((i = 0; i < DB_WAIT_SECONDS; i += 2)); do
    if compose exec -T db sh -c \
      'MYSQL_PWD="$MARIADB_PASSWORD" mariadb-admin ping -h 127.0.0.1 -u"$MARIADB_USER" --silent' \
      >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  die "database not ready after ${DB_WAIT_SECONDS}s"
}

backup() {
  mkdir -p "$BACKUP_DIR"
  local file="$BACKUP_DIR/embrella_$(date +%Y-%m-%d_%H%M%S).sql.gz"
  local tmp="$file.tmp"
  trap "rm -f '$tmp'" EXIT

  # --single-transaction: consistent snapshot without locking, so Embrella stays up.
  compose exec -T db sh -c \
    'MYSQL_PWD="$MARIADB_PASSWORD" mariadb-dump -u"$MARIADB_USER" --databases "$MARIADB_DATABASE" --add-drop-database --single-transaction' \
    | gzip >"$tmp"

  is_complete "$tmp" || die "dump incomplete; no backup written"
  mv "$tmp" "$file"
  echo "Backup written: $file"
}

restore() {
  local file="${1:-}"
  [ -n "$file" ] || die "usage: $0 restore <file>"
  [ -f "$file" ] || die "no such file: $file"
  is_complete "$file" || die "$file is not a complete backup"

  read -r -p "Replace the current database with $file? Embrella will be down meanwhile. [y/N] " answer
  [ "$answer" = "y" ] || die "aborted"

  # Only db runs, so nothing writes during the restore.
  compose down
  compose up -d db
  wait_for_db

  cat_dump "$file" | compose exec -T db sh -c \
    'MYSQL_PWD="$MARIADB_PASSWORD" mariadb -u"$MARIADB_USER"'

  # 'up' runs migrate before backend and worker start.
  compose up -d
  echo "Restored: $file"
}

case "${1:-}" in
  backup) backup ;;
  restore) restore "${2:-}" ;;
  *) die "usage: $0 backup | restore <file>" ;;
esac
