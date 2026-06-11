# Container Layout

Everything to run Embrella in containers lives in the repo's `infra/` directory.
Three target environments (dev, staging, prod) share one set of Dockerfiles and a
base compose file; each environment is a thin overlay.

For first-time local setup, start with [Getting Started](gettingstarted.md)

## Day-to-day commands development

```
# on host cli
just dbbackupv2 staging
just loadcontainerdb
just deployv2 staging <envfile> <branch> <tag>
just fetchprodsnapshot      # get a recent snapshot to use for dev
```

```
# in devcontainer
just loaddevdb <snapshot>
just dbbackupdev
```

Run `just --list --unsorted` for the full set with details

## One-time setup on a fresh host

**Resources.** Give your container engine enough headroom — the full stack
(MariaDB + Django + worker + Next.js + nginx, plus image builds and the Playwright
browsers) is heavy. Recommended: **16 GB RAM / 8 CPUs / 50 GB disk**.

```
# Docker Desktop: Settings → Resources → set Memory at least 16 GB, Disk ≥ 50 GB

# for podman
podman machine stop
podman machine set --memory 16384 --cpus 8 --disk-size 50
podman machine start
```

## Devcontainer

A single full-stack devcontainer lives at `.devcontainer/devcontainer.json`. It
attaches to the running `backend` compose service, mounts the whole repo
(including `.git/`) at `/app`, and adds Node, `gh`, Claude Code, and other extensions.

- **Auth + settings + shell history persist** across rebuilds via three named
  volumes scoped per project with `${devcontainerId}`:
  `claude-code-config-*`, `gh-config-*`, `shell-history-*`.
- **Git identity** comes from your host `~/.gitconfig` (bind-mounted, read-only).
  Push auth can go through `gh` over HTTPS.
- **SSH agent forwarding** is available for git-over-SSH and cluster operations
  without copying any private keys into the container.
- **Browser automation** via the Playwright MCP server
  to verify UI changes against `http://nginx` or `http://frontend:3000`
  from inside the container.

A host-side precheck for devcontainer runs (`.devcontainer/precheck_embrella_requirements.sh`)

Open in VS Code with "Dev Containers: Reopen in Container" → "Embrella". On first
run: `claude` to sign in, then `gh auth login` for git push.

## Environment variable conventions

The services read these. Defaults come from `.env` / `.env.<stage>` at repo root.

| Variable                   | Where read                         | Notes                                                                                                                         |
| -------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `DJANGO_ENV`               | settings.py                        | `development` enables DEBUG.                                                                                                  |
| `USE_MYSQL`                | settings.py + entrypoint           | `True` to use MySQL/MariaDB.                                                                                                  |
| `MYSQL_HOST/USER/PWD/NAME` | settings.py                        | `MYSQL_HOST=db` inside the network.                                                                                           |
| `EMBRELLA_BUILD_STATIC`    | entrypoint                         | `1` → collectstatic + mkdocs build. Set only on prod/staging web.                                                             |
| `EMBRELLA_MIGRATE`         | entrypoint                         | `1` → run DB migrations. Set only on the one-shot `migrate` service; backend + worker wait on it.                             |
| `SLURM_KEYFILE`            | clusterio.py                       | In-container path. Dev overrides to `/run/secrets/slurm_key`.                                                                 |
| `DEBUGPY_LISTEN`           | manage.py                          | `1` opens a debugpy listener on `DEBUGPY_PORT`.                                                                               |
| `NGINX_RESOLVER`           | nginx\_\*.conf.template (envsubst) | DNS server nginx uses to re-resolve upstreams. Defaults to internal gateway IP (podman); override to `127.0.0.11` for Docker. |
| `IMAGE_TAG`                | compose.yaml                       | Image tag for both backend + frontend (default `latest`).                                                                     |

## Debugging

The backend and worker call `debugpy.listen(("0.0.0.0", DEBUGPY_PORT))` at startup
when `DEBUGPY_LISTEN=1` (set for both in `infra/compose.dev.yaml`). Ports are published to the
host: **backend `localhost:5678`**, **worker `localhost:5679`**.

### VS Code

Launch config for debugging is at `.vscode/launch.json` and attaches with F5. This is wired for the **devcontainer** flow (VS Code running inside the `backend`
container).

Tests are preconfigured to be run through the Testing module for Jest, Playwright, and Pytest.

### Frontend

Client-side React / `.tsx` debugging goes through the browser — `http://localhost:8080` (through
nginx) or `http://localhost:3000` (direct to Next.js). Server-side Next.js
debugging (Node inspector attach) is not wired up yet.

## Logs

Container stdout/stderr only. No file-on-disk logs.

```
just devlogs                 # tail everything
just devlogs backend         # one service
podman logs embrella-backend-1
```

## Common operations

### Reset the dev database

```
just devdown
podman volume rm embrella_db_data
just devup
```

### Back up / restore a database

```
just dbbackupdev                          # dump the dev compose db → ./.scratch/
just loaddevdb <snapshot.sql>             # restore a snapshot into the dev db
just dbbackupv2 prod                      # on-demand dump of a prod/staging container db
just loadcontainerdb prod <snapshot.sql>  # restore into a prod/staging container db
```

### Migrations and seed data

Migrations run automatically. The one-shot `migrate` service applies them on
every `just devup` (it owns the `stores` → `projects` → rest ordering; see
`entrypoint-backend.sh`).

To re-apply migrations on demand (e.g. after pulling new migration files), re-run
the `migrate` service

```
podman compose --env-file .env -f infra/compose.yaml -f infra/compose.dev.yaml run --rm migrate
```

### Reload nginx after editing the dev conf template

```
podman exec embrella-nginx-1 nginx -s reload
```

(The template is bind-mounted, so editing it on host takes effect on reload.)

### Try staging compose locally without deploying

```
podman compose --env-file .env -f infra/compose.yaml -f infra/compose.staging.yaml config
# prints the resolved config — doesn't start anything
```

## Files

| File                          | Role                                                                                                                                                                                                                                                                                                                                                                     |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `infra/backend.Dockerfile`    | Multi-stage build for the Django image (used by `backend` + `worker`).                                                                                                                                                                                                                                                                                                   |
| `infra/frontend.Dockerfile`   | Multi-stage build for the Next.js image.                                                                                                                                                                                                                                                                                                                                 |
| `infra/entrypoint-backend.sh` | Runs at every backend/worker/migrate container start. Waits for the DB, runs migrations only when `EMBRELLA_MIGRATE=1` (the one-shot `migrate` service), optionally builds static + docs.                                                                                                                                                                                |
| `infra/compose.yaml`          | **Base.** Service shapes, networks, named volumes. Never run alone — pair with an overlay.                                                                                                                                                                                                                                                                               |
| `infra/compose.dev.yaml`      | Dev overlay. Bind-mounts the whole repo at `/app` (so `.git/`, `Justfile`, configs are all visible inside the container), masks `.venv` with the `backend_venv` named volume, shares the `frontend_node_modules` + `frontend_next` volumes into the backend container so frontend tests run there too, mounts the SLURM key + `~/.gitconfig`, and publishes debug ports. |
| `infra/compose.staging.yaml`  | Staging overlay. Pulls prebuilt images, uses staging nginx conf, expects a `slurm_key` podman secret.                                                                                                                                                                                                                                                                    |
| `infra/compose.prod.yaml`     | Production overlay. Same shape as staging with prod nginx conf and TLS port.                                                                                                                                                                                                                                                                                             |
