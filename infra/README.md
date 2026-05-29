# infra/ — container layout

Everything to run Embrella in containers lives here. Three target environments
(dev, staging, prod) share one set of Dockerfiles and a base compose file; each
environment is a thin overlay.

## Files

| File | Role |
| --- | --- |
| `backend.Dockerfile`            | Multi-stage build for the Django image (used by `backend` + `worker`). |
| `frontend.Dockerfile`           | Multi-stage build for the Next.js image. |
| `entrypoint-backend.sh`         | Runs at every backend/worker container start. Waits for the DB, runs migrations, optionally builds static + docs. |
| `compose.yaml`                  | **Base.** Service shapes, networks, named volumes. Never run alone — pair with an overlay. |
| `compose.dev.yaml`              | Dev overlay. Bind-mounts the whole repo at `/app` (so `.git/`, `Justfile`, configs are all visible inside the container), masks `.venv` with the `backend_venv` named volume, shares the `frontend_node_modules` + `frontend_next` volumes into the backend container so frontend tests run there too, mounts the SLURM key + `~/.gitconfig`, and publishes debug ports. |
| `compose.staging.yaml`          | Staging overlay. Pulls prebuilt images, uses staging nginx conf, expects a `slurm_key` podman secret. |
| `compose.prod.yaml`             | Production overlay. Same shape as staging with prod nginx conf and TLS port. |
| `nginx_dev.conf.template`       | Dev nginx config. `${NGINX_RESOLVER}` is `envsubst`'d at container startup. |
| `nginx_staging.conf`            | Staging nginx config. Routes /api/admin/etc → `backend:8000`, everything else → `frontend:3000`. |
| `nginx_production.conf`         | Same as staging, different server_name. |

Related, one level up:

| File | Role |
| --- | --- |
| `../.devcontainer/devcontainer.json` | Single full-stack devcontainer attached to the `backend` service. Adds Node 20, `gh`, `just`, Claude Code, and Playwright MCP on top of the backend image; persists Claude auth + `gh` auth + shell history across rebuilds via per-project named volumes. |
| `../.mcp.json`                       | Project-scoped MCP servers. Currently exposes Playwright so Claude can drive a headless browser to verify UI changes. |
| `../.dockerignore`                   | Excludes from the image build context. `.git/` is excluded from images but bind-mounted in dev. |

## Day-to-day commands

```
just devup       # bring up the full dev stack
just devdown     # stop and remove containers (volumes survive)
just devlogs [service]
just devexec <cmd>     # one-off command inside the running backend container
just devshell          # interactive zsh shell inside the backend container (embrella user)
just uvadd <pkg>       # add Python dep + sync into running .venv
just buildimages <tag> # build the two images for staging/prod push
just deployv2 staging staging
```

See the project root [Justfile](../Justfile) for the full set.

## Stack shape

Five services on two networks:

```
┌─────────────────────────── internal (10.89.200.0/24) ───────────────────────────┐
│                                                                                  │
│   ┌─────────┐    ┌──────────┐    ┌────────┐    ┌────────┐    ┌──────────────┐   │
│   │   db    │◄───┤ backend  │    │ worker │    │frontend│    │    nginx     │───┼─► host :8080
│   │ mariadb │    │  django  │    │qcluster│    │next dev│    │  routes →    │   │   (dev)
│   └─────────┘    └──────────┘    └────────┘    └────────┘    └──────┬───────┘   │
│                                                                     │           │
└─────────────────────────────────────────────────────────────────────┼───────────┘
                                                                      │
                                              ┌───────────────────────┼───────────┐
                                              │   embrella  (external)│           │
                                              │                       │           │
                                              │   other org apps ◄────┘           │
                                              │   (copick-web, etc.)              │
                                              └───────────────────────────────────┘
```

- `internal` is project-private. Pinned to `10.89.200.0/24` so the gateway IP
  (which is podman's aardvark DNS) is stable and nginx's `resolver` directive
  can point at a known address.
- `embrella` is an **external** network created once per host
  (`podman network create embrella` or `just netinit`). Only nginx joins it.
  Other containerized org apps attach to this network and become reachable
  through embrella's nginx by service DNS.

## One-time setup on a fresh host

**Resources.** Give your container engine enough headroom — the full stack
(MariaDB + Django + worker + Next.js + nginx, plus image builds and the
Playwright browsers) is heavy. Set the VM to at least:

- **Memory:** 8192 MB (8 GB) RAM
- **Disk:** 50 GB

On macOS/Windows this is the Podman machine or Docker Desktop VM:

```
podman machine set --memory 8192 --disk-size 50      # podman (recreate/restart the machine after)
# Docker Desktop: Settings → Resources → set Memory 8 GB, Disk ≥ 50 GB
```

```
podman network create embrella                          # all envs
podman secret create slurm_key /path/to/svc_czii_umbrella   # staging/prod only
```

For dev, `just netinit` does the network step. The SLURM key on dev is bind-
mounted from the path in `.env`'s `SLURM_KEYFILE` (typically
`~/.ssh/svc_czii_umbrella`).

## Environment variable conventions

The services read these. Defaults come from `.env` / `.env.<stage>` at repo root.

| Variable | Where read | Notes |
| --- | --- | --- |
| `DJANGO_ENV`                | settings.py | `development` enables DEBUG. |
| `USE_MYSQL`                 | settings.py + entrypoint | `True` to use MySQL/MariaDB. |
| `MYSQL_HOST/USER/PWD/NAME`  | settings.py | `MYSQL_HOST=db` inside the network. |
| `EMBRELLA_BUILD_STATIC`     | entrypoint | `1` → collectstatic + mkdocs build. Set only on prod/staging web. |
| `SLURM_KEYFILE`             | clusterio.py | In-container path. Dev overrides to `/run/secrets/slurm_key`. |
| `DEBUGPY_LISTEN`            | manage.py | `1` opens a debugpy listener on `DEBUGPY_PORT`. |
| `NGINX_RESOLVER`            | nginx_*.conf.template (envsubst) | DNS server nginx uses to re-resolve upstreams. Defaults to internal gateway IP (podman); override to `127.0.0.11` for Docker. |
| `IMAGE_TAG`                 | compose.yaml | Image tag for both backend + frontend (default `latest`). |

## Devcontainer

A single full-stack devcontainer lives at [`../.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json).
It attaches to the running `backend` compose service, mounts the whole repo
(including `.git/`) at `/app`, and adds Node 20, `gh`, Claude Code, and the
Playwright MCP server on top of the Python backend image — so both `pytest` and
`yarn test` run from one shell. Following Anthropic's
[devcontainer guide](https://code.claude.com/docs/en/devcontainer):

- **Claude Code** is installed via `ghcr.io/anthropics/devcontainer-features/claude-code`.
- **Auth + settings + shell history persist** across rebuilds via three named
  volumes scoped per project with `${devcontainerId}`:
  `claude-code-config-*`, `gh-config-*`, `shell-history-*`.
- **Git identity** comes from your host `~/.gitconfig` (bind-mounted, read-only).
  Push auth goes through `gh` over HTTPS — `~/.ssh` is intentionally not
  mounted, per Anthropic's recommendation.
- **Browser automation** via the Playwright MCP server (configured in
  [`../.mcp.json`](../.mcp.json)) lets Claude verify UI changes against
  `http://nginx` or `http://frontend:3000` from inside the container.

**Before opening:** you need an `.env` at the repo root — the devcontainer
won't start without it. Copy the template and fill it in:

```bash
cp helpers/.env_template .env
# edit .env: set the real values and delete the YOUDIDNOTUPDATETHIS line.
# Leave SLURM_KEYFILE empty unless you have a cluster key on this host.
```

A host-side precheck ([`../.devcontainer/precheck_embrella_requirements.sh`](../.devcontainer/precheck_embrella_requirements.sh),
run from `initializeCommand`) verifies this and a few other prerequisites
before any container is built, failing early with a clear message instead of a
cryptic compose mount error.

Open in VS Code with "Dev Containers: Reopen in Container" → "Embrella
Full-Stack". On first run: `claude` to sign in, then `gh auth login` for git
push.

### Claude Code auth: API key (recommended for devcontainers)

The interactive `claude` login flow hangs inside the devcontainer because the
OAuth callback redirects to `localhost:<port>` on your host, which can't reach
the container. The cleanest workaround is to authenticate with an
`ANTHROPIC_API_KEY` and forward it from the host:

1. **Get an API key.** From [console.anthropic.com](https://console.anthropic.com)
   → Settings → API Keys, or extract a key already provisioned on your host:
   ```bash
   security find-generic-password -s "Claude Code" -w
   ```
   (macOS Keychain — works if you've previously logged in to Claude Code on
   the host.)

2. **Export it on the host**, e.g. in `~/.zshrc`:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-api-...
   ```
   Re-source the file (`source ~/.zshrc`) and verify with
   `echo ${ANTHROPIC_API_KEY:0:15}`.

3. **Forward it into the container.** Already wired into
   [`../.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json)
   via:
   ```json
   "containerEnv": {
     "ANTHROPIC_API_KEY": "${localEnv:ANTHROPIC_API_KEY}"
   }
   ```
   Only the variable *name* is committed; the value is read from the host at
   container-start time.

4. **Rebuild the container** (Command Palette → "Dev Containers: Rebuild
   Container"). A plain reopen won't pick up `containerEnv` changes. Then
   inside the container, `env | grep ANTHROPIC` should show the key and
   `claude` should start without hanging.

If you have a Claude subscription seat instead of API access, swap
`ANTHROPIC_API_KEY` for `CLAUDE_CODE_OAUTH_TOKEN` (generated on the host with
`claude setup-token`) — same wiring otherwise.

## Debugging

Backend/worker expose `debugpy` on `localhost:5678` / `localhost:5679`. VS Code
attach configs ship with [`../.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json)
(under `customizations.vscode.launch`). PyCharm/JetBrains setup is documented in
[../.claude/plans/dockerize-embrella.md](../.claude/plans/dockerize-embrella.md#debugger-support).

For frontend, client-side debugging goes through the browser (Chrome DevTools
or PyCharm's "JavaScript Debug" config against `http://localhost:8080`). Server-side
Next.js debugging (Node inspector attach) is **not wired up** — Next.js spawns
worker processes that fight over the inspector port and put the dev server in a
restart loop. Revisit after a Next.js upgrade.

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

### Manually run migrations or seed data
```
just devexec python umbrella/manage.py migrate
just devexec just populatedbexamples
```

### Reload nginx after editing the dev conf template
```
podman exec embrella-nginx-1 nginx -s reload
```
(The template is bind-mounted, so editing it on host takes effect on reload.)

### Try staging compose locally without deploying
```
podman compose -f infra/compose.yaml -f infra/compose.staging.yaml config
# prints the resolved config — doesn't start anything
```

## macOS: bumping the podman machine

On macOS, podman runs inside a VM. The default (4 GB RAM, ~60 GB disk) is tight
once you're running all five services plus a devcontainer attached to `backend`
— Jest, Next.js builds, and Playwright tend to blow past 4 GB. Recommended:

```
podman machine stop
podman machine set --memory 8192 --cpus 4 --disk-size 100
podman machine start
```

(`--memory` is MB, `--disk-size` is GB.) Inspect current values with
`podman machine inspect` or `podman machine ls`. Check how much of the VM disk
is in use with `podman system df`.

If `podman machine set` rejects a disk-size change (older podman versions),
recreate the machine: `podman machine rm` then `podman machine init --memory
8192 --cpus 4 --disk-size 100`. Recreating wipes images and named volumes —
plan for a fresh `just devup --build`.

## Cross-engine notes

Defaults target **podman** (rootless on macOS via `podman machine`). For Docker
users, override `NGINX_RESOLVER=127.0.0.11` in your shell or `.env` —
Docker's embedded DNS lives there, while podman's aardvark-dns is on the
network gateway.
