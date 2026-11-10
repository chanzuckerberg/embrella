# Environment Variables

Embrella reads its settings from
[`docker-compose.env`](https://github.com/chanzuckerberg/embrella/blob/main/docker/compose/docker-compose.env),
beside `docker-compose.yml`. Each setting is a `key=value` line; list values are
comma-separated.

## Core

| Variable            | Required | Default | Notes                                                        |
| ------------------- | -------- | ------- | ------------------------------------------------------------ |
| `DJANGO_SECRET_KEY` | yes      |         | Unique per deployment. Generate with `openssl rand -hex 32`. |
| `TIME_ZONE`         |          | `UTC`   | IANA name, e.g. `America/Los_Angeles`.                       |

## Hosts and security

| Variable                   | Required    | Default | Notes                                                                                                                                  |
| -------------------------- | ----------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `EMBRELLA_HOSTS`           | production  |         | Public hostnames. Bare host = https; prefix `http://` if no TLS; leading dot = any subdomain. e.g. `embrella.example.org,.example.org` |
| `FILESERVER_ALLOWED_HOSTS` | recommended | any     | Origins the file server may use, e.g. `https://files.example.org`.                                                                     |

!!! warning

    An empty `FILESERVER_ALLOWED_HOSTS` allows any origin, so a tampered cluster
    `http_base_url` could point users or the server at any host.

## Sign-in

| Variable                   | Required | Default | Notes                                                                                |
| -------------------------- | -------- | ------- | ------------------------------------------------------------------------------------ |
| `GOOGLE_SSO_CLIENT_ID`     | for SSO  |         | Google OAuth client.                                                                 |
| `GOOGLE_SSO_CLIENT_SECRET` | for SSO  |         |                                                                                      |
| `SSO_ALLOWED_DOMAINS`      | for SSO  | nobody  | Email domains allowed to sign in, e.g. `example.org`. `*` admits any Google account. |

## Cluster

| Variable                 | Required    | Default | Notes                                                                                                                                                               |
| ------------------------ | ----------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SSH_DISABLED`           |             | `True`  | Set `False` to enable cluster access.                                                                                                                               |
| `SLURM_USER`             | for cluster |         | Service account on the cluster.                                                                                                                                     |
| `DEPOSITION_AWS_PROFILE` |             | unset   | Optional profile from the cluster service account's `~/.aws` files for deposition upload jobs. If unset, jobs use the account's existing AWS configuration or role. |

!!! note

    The service account's SSH key is not a setting. Place it beside
    `docker-compose.yml` as `slurm_key` and enable its mounts; see
    [Deployment](deployment.md#installation).

## Reservation IDs (CryoET Data Portal deposition)

The CryoET Data Portal deposition feature reserves dataset and deposition IDs from a Lambda.

| Variable                 | Required | Default | Notes                                                                                          |
| ------------------------ | -------- | ------- | ---------------------------------------------------------------------------------------------- |
| `RESERVATION_LAMBDA_URL` |          | unset   | Reservation lambda URL. Required unless `DJANGO_ENV=development` (dev uses an in-memory stub). |
| `AWS_PROFILE`            |          | unset   | Profile for signing reservation calls, read by the backend container.                          |

!!! note

    Signing needs AWS credentials available to the backend container.
    Staging/prod overlays mount the file at `EMBRELLA_AWS_CREDENTIALS_FILE`;
    the dev overlay mounts `~/.aws`. `AWS_PROFILE` is separate from
    `DEPOSITION_AWS_PROFILE`, which is for cluster upload jobs.
