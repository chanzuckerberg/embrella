#!/usr/bin/env bash
# Runs once after the devcontainer is created. See devcontainer.json.
set -euo pipefail

# Devcontainer-only named volumes are created empty as root; chown them so
# the `embrella` user can write. (/app/.venv is owned by `embrella` in the
# backend image already, so its named volume seeds correctly.)
sudo chown -R embrella:embrella \
  /commandhistory \
  /home/embrella/.claude \
  /home/embrella/.config/gh \
  /home/embrella/.cache

# `/app` is bind-mounted from the host, so git sees a different owner.
sudo git config --system --add safe.directory /app

# Pin yarn version and install the playwright MCP server for Claude Code.
corepack enable
corepack prepare yarn@4.9.1 --activate
npm install -g @playwright/mcp@latest

# Image's venv was built with --no-default-groups. Install the `dev` group
# (pytest, ruff, debugpy) on top so `pytest` / `ruff` / debug attach work.
uv sync --locked

# Install Playwright browsers into the persistent ms-playwright cache volume
# so the VS Code Playwright extension and `yarn e2e` work without manual setup.
# The playwright bin lives in the frontend service's shared node_modules
# (mounted at /app/frontend/node_modules via the frontend_node_modules named
# volume), so wait until the frontend container has finished `yarn install`.
playwright_bin=/app/frontend/node_modules/.bin/playwright
for _ in $(seq 1 60); do [[ -x "$playwright_bin" ]] && break; sleep 2; done
if [[ -x "$playwright_bin" ]]; then
  # System libs (glib, nss, etc.) for chromium — backend image is python:3.11-slim
  # which lacks them. Re-installed on each container rebuild; not baked into the
  # backend Dockerfile so prod runtime stays lean.
  # sudo strips PATH, so node from nvm isn't found — preserve it explicitly.
  (cd /app/frontend && sudo env "PATH=$PATH" "$playwright_bin" install-deps chromium)
  (cd /app/frontend && "$playwright_bin" install chromium)
else
  echo "post-create: frontend node_modules not ready after 120s — skipping"
  echo "post-create: run \`cd /app/frontend && sudo yarn playwright install-deps chromium && yarn playwright install chromium\` manually"
fi
