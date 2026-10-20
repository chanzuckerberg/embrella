# Deployment

Choose the installation route that best fits your setup:

| Route                             | Best for                                  |
| --------------------------------- | ----------------------------------------- |
| [Docker Compose](#docker-compose) | Most hosts (recommended)                  |
| [Podman Compose](#podman-compose) | Rootless hosts, or hosts without Docker   |
| [Bare metal](#bare-metal-legacy)  | Hosts without a container engine (legacy) |

## Docker Compose Install {#docker-compose}

#### Prerequisites

- Docker and Docker Compose must be [installed](https://docs.docker.com/engine/install/).
- The [prerequisites](gettingstarted.md#production-requirements): a cluster service account and a
  file server.

#### Installation

1.  Go to the [/docker/compose directory on the project page](https://github.com/chanzuckerberg/embrella/tree/main/docker/compose)
    and download `docker-compose.yml`, `docker-compose.env` and `nginx.conf` into a
    local directory:

    ```bash
    mkdir -p /srv/embrella && cd /srv/embrella
    BASE=https://raw.githubusercontent.com/chanzuckerberg/embrella/main/docker/compose
    curl -fsSLO $BASE/docker-compose.yml
    curl -fsSLO $BASE/docker-compose.env
    curl -fsSLO $BASE/nginx.conf
    ```

2.  Copy the service account's SSH private key into the same directory as `slurm_key`:

    ```bash
    cp /path/to/key slurm_key
    ```

    !!! tip "Generating a key"

        [SSH key guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key).
        Embrella requires an Ed25519 key with no passphrase. Instead of adding the public
        key to GitHub, append it to the service account's `~/.ssh/authorized_keys` on the
        cluster.

3.  Modify `docker-compose.yml` as needed:
    - Uncomment the `slurm_key` mounts on `backend` and `worker`.
    - Change the database password, `embrella` by default, in both `MYSQL_PWD` and
      `MARIADB_PASSWORD`. Also change `MARIADB_ROOT_PASSWORD`.
    - You may want to change the port the nginx container listens on from the default (8080) to
      something else, e.g. for port 80:

      ```yaml
      ports:
        - 80:80
      ```

    !!! warning

        Change the database password before the first `docker compose up`. The
        database keeps the password it was created with.

4.  Modify `docker-compose.env` with the configuration options you need. See
    [Environment Variables](environment.md) for all options. At minimum, set
    `DJANGO_SECRET_KEY`, `EMBRELLA_HOSTS`, `SSH_DISABLED=False` and `SLURM_USER`.
    Setting `FILESERVER_ALLOWED_HOSTS` is recommended.

    !!! tip

        Generate a secret key with `openssl rand -hex 32`.

5.  Run `docker compose pull`. This pulls the images from the GitHub container registry.

6.  Run `docker compose up -d`. This creates and starts the containers, and runs
    database migrations.

#### After installation

Create your admin account:

```bash
docker compose exec backend python umbrella/manage.py createsuperuser
```

Embrella is now available at `http://<host>:8080` (or the port you chose).

!!! note

    Embrella serves plain HTTP. Terminate TLS in front of it with your institution's
    reverse proxy or load balancer.

#### Upgrading

!!! warning

    Always [back up the database](#backups) before upgrading.

```bash
docker compose pull
docker compose up -d
```

#### Backups {#backups}

Data lives in the `dbdata` volume. Download
[`database_commands.sh`](https://github.com/chanzuckerberg/embrella/blob/main/docker/database_commands.sh)
beside `docker-compose.yml`:

```bash
curl -fsSLO https://raw.githubusercontent.com/chanzuckerberg/embrella/main/docker/database_commands.sh
chmod +x database_commands.sh
```

It uses `docker compose`, or `podman compose` if Docker is absent.

Back up:

```bash
./database_commands.sh backup
```

This writes `backups/embrella_<timestamp>.sql.gz` while Embrella keeps running.

Restore:

```bash
./database_commands.sh restore backups/embrella_<timestamp>.sql.gz
```

!!! warning

    Embrella is down during a restore. Restores take longer than backups, so plan downtime accordingly.

## Podman Compose Install {#podman-compose}

For rootless hosts. Podman uses the same files as [Docker Compose](#docker-compose).

#### Prerequisites

- [Podman](https://podman.io/docs/installation) with `podman compose`.
- A compose provider for `podman compose` to call, e.g. `docker-compose` v2+.

#### Installation

Follow the [Docker Compose installation](#installation) steps, with `podman compose`
in place of `docker compose`:

```bash
podman compose pull
podman compose up -d
podman compose exec backend python umbrella/manage.py createsuperuser
```

!!! note

    Rootless Podman needs a subordinate UID range for your user, so containers can
    run as their own users. If containers fail with permission errors, add one:

    ```bash
    sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $USER
    podman system migrate
    ```

!!! warning

    Rootless Podman can't bind ports below 1024. Keep the default 8080, or allow
    lower ports with `sudo sysctl net.ipv4.ip_unprivileged_port_start=80`.

#### macOS

The images are `amd64` only. On Apple Silicon, Podman's default `qemu` emulation
crashes the backend (`Segmentation fault` in `migrate`). Run them under Rosetta
instead:

1.  Install Rosetta:

    ```bash
    softwareupdate --install-rosetta --agree-to-license
    ```

2.  Enable it in `~/.config/containers/containers.conf`:

    ```toml
    [machine]
    rosetta = true
    ```

3.  Create an `applehv` machine (`libkrun` lacks Rosetta):

    ```bash
    podman machine init --provider applehv --memory 8192 embrella
    podman machine start embrella
    podman system connection default embrella
    ```

## Deposition staging and uploads {#deposition-staging}

Deposition prep, upload, monitoring, cancellation and log reads all run as the
configured cluster service account. Set `SLURM_USER` and provide its SSH key to
both the backend and worker, the same key as the `slurm_key` mount above.
Submitters do not need their own SSH or AWS credentials; Embrella still records
the submitting user.

#### Setup

1.  Create a staging directory the service account can write to. It must also be
    able to read the source data and follow the staged symlinks. The enclosing
    directory need not be group-writable.

2.  In Django admin, under **Stores → Path types**, add a `deposition_staging`
    row for the target cluster. Set its `overlay_path` to an absolute directory
    template containing `{deposition_id}`, for example:

    ```text
    /srv/portal/staging/{deposition_id}/
    ```

3.  Make AWS credentials available to the service account on the compute nodes,
    with access to the S3 destination set by `deposition_sync_destination`.
    Directory permissions do not grant AWS access.

    To use a named profile from the service account's `~/.aws` files, set
    `DEPOSITION_AWS_PROFILE` in the backend and worker environment. If unset,
    upload jobs use the account's existing AWS configuration or role.
    Restart the backend and worker with the updated environment. Jobs already
    submitted keep their previous profile.

Prep writes its config and dataset subdirectories beneath the staging path, and
push reads those same subdirectories.

!!! note

    Check for an existing cluster-specific `deposition_staging` row before
    adding one. Edit that override if present; otherwise add a new row for the
    target cluster. Editing the cluster-agnostic seed changes the default for
    every cluster without its own override.

!!! warning

    Before switching accounts or changing the path, finish existing deposition
    jobs and uploads, or arrange migration of their staged data and permissions.
    Updating a PathType does not move existing data. Verify a small prep and
    upload from the deployed backend and worker before enabling the flow.

### Pre-flight validation {#deposition-validation}

After sync, prep runs `cryoetportalprep push <config> --dry-run` for the current
dataset only. Upload is enabled only when this passes for the current prep attempt.
Failed, missing or unavailable results block upload, and users can retry preparation
or choose **Fix and re-prepare** to edit metadata first. Diagnostics are visible only
to the submission owner.

The result comes from the dry run's **exit code** (messages are best-effort text
matches), so the installed CLI must exit nonzero on an invalid config.

## Bare Metal Install {#bare-metal-legacy}

Runs Django, Next.js and the task worker directly on the host, against a MariaDB/MySQL
server you provide.

!!! warning

    Not recommended for new installs. Use [Docker Compose](#docker-compose) instead.

See [Contributing → Getting Started, Path B](../contributing/gettingstarted.md#path-b-bare-metal-legacy).
