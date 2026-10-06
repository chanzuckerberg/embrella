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

| Variable       | Required    | Default | Notes                                 |
| -------------- | ----------- | ------- | ------------------------------------- |
| `SSH_DISABLED` |             | `True`  | Set `False` to enable cluster access. |
| `SLURM_USER`   | for cluster |         | Service account on the cluster.       |

!!! note

    The service account's SSH key is not a setting. Place it beside
    `docker-compose.yml` as `slurm_key` and enable its mounts; see
    [Deployment](deployment.md#installation).
