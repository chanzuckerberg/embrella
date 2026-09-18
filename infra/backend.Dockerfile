# syntax=docker/dockerfile:1

# ---- deps stage: build the venv with uv ----
FROM python:3.11-slim AS deps

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.9.4 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-default-groups

# ---- app stage: everything both `runtime` and `test` need ----
FROM python:3.11-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update && apt-get install -y --no-install-recommends \
      openssh-client \
      curl \
      ca-certificates \
      tini

COPY --from=ghcr.io/astral-sh/uv:0.9.4 /uv /uvx /usr/local/bin/
COPY --from=deps /app/.venv /app/.venv

WORKDIR /app

COPY umbrella ./umbrella
COPY docs ./docs
COPY mkdocs.yml pyproject.toml uv.lock ./
COPY infra/entrypoint-backend.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /app/umbrella/staticfiles /app/docs_build

# Non-root user (uid/gid 1000) so files written into bind mounts and named
# volumes match the devcontainer's `remoteUser` and the host caller's uid.
RUN groupadd -g 1000 embrella \
 && useradd  -u 1000 -g 1000 -m -s /bin/bash embrella \
 && chown -R embrella:embrella /app /entrypoint.sh

USER embrella

# ---- test stage: adds the `dev` group (pytest, ruff) of packages
FROM app AS test
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/home/embrella/.cache/uv,uid=1000,gid=1000 uv sync --locked

# ---- dev stage: adds the MariaDB CLI (mysql/mysqldump) for loaddevdb,
# dbbackupdev and ad-hoc queries. Dev only — staging/prod never need it.
FROM test AS dev
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      default-mysql-client
USER embrella
# Same entrypoint as `runtime`: compose's `migrate` service runs `true` and
# relies on the entrypoint (EMBRELLA_MIGRATE=1) to apply migrations.
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]

# ---- runtime stage ----
FROM app AS runtime

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["gunicorn", "umbrella.wsgi", "--chdir", "umbrella", "--bind", "0.0.0.0:8000", "--workers", "4", "--access-logfile", "-", "--error-logfile", "-"]
