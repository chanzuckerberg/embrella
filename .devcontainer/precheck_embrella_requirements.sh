#!/usr/bin/env bash
# Host-side precheck for the devcontainer. Runs from devcontainer.json's initializationCommand
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

err() { echo "❌ $*" >&2; }

# 1. .env is required. for compose.dev.yaml's env_file
echo "Checking for .env file at the repo root..."
if [[ ! -f .env ]]; then
  err "No .env file at the repo root — the devcontainer can't start without it."
  err ""
  err "    cp helpers/.env_template .env"
  err ""
  err "Then edit .env (fill in the values and delete the YOUDIDNOTUPDATETHIS line)."
  exit 1
fi

# 2. Don't let an unconfigured template through
echo "Checking .env for unconfigured values..."
if grep -q '^YOUDIDNOTUPDATETHIS=' .env; then
  err ".env still has the YOUDIDNOTUPDATETHIS placeholder line."
  err "Fill in the real values, then delete that line and re-run."
  exit 1
fi

# 3. SLURM key is optional. The compose mount falls back to /dev/null when
#    SLURM_KEYFILE is empty, but a non-empty path that doesn't exist makes the
#    bind mount fail — catch it here with an actionable hint.
slurm_keyfile="$(grep -E '^SLURM_KEYFILE=' .env | tail -1 | cut -d= -f2- | tr -d '"' || true)"
if [[ -n "$slurm_keyfile" && ! -f "$slurm_keyfile" ]]; then
  err "SLURM_KEYFILE in .env points at a file that doesn't exist:"
  err "    $slurm_keyfile"
  err "Fix the path, or leave SLURM_KEYFILE empty to run without cluster access."
  exit 1
fi

# 4. ~/.gitconfig is bind-mounted read-only for in-container commits. Create an
#    empty one if absent so the mount source exists (empty is harmless).
echo "Checking for ~/.gitconfig..."
if [[ ! -f "$HOME/.gitconfig" ]]; then
  echo "ℹ️  creating an empty ~/.gitconfig so the git-identity mount has a source"
  touch "$HOME/.gitconfig"
fi

# 5. nginx joins the shared external `embrella` network; create it once if it's
#    not there yet (idempotent).
podman network inspect embrella >/dev/null 2>&1 || podman network create embrella

echo "✅ Embrella Ready for DevContainer Creation"
