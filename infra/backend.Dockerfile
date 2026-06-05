# syntax=docker/dockerfile:1

# ---- deps stage: build the venv with uv ----
FROM python:3.11-slim AS deps

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      pkg-config \
      default-libmysqlclient-dev \
      git \
      curl \
      ca-certificates \
      openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.4 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-default-groups

# ---- runtime stage ----
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV=/app/.venv

RUN apt-get update && apt-get install -y --no-install-recommends \
      default-libmysqlclient-dev \
      default-mysql-client \
      openssh-client \
      curl \
      ca-certificates \
      tini \
    && rm -rf /var/lib/apt/lists/*

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

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["gunicorn", "umbrella.wsgi", "--chdir", "umbrella", "--bind", "0.0.0.0:8000", "--workers", "4", "--access-logfile", "-", "--error-logfile", "-"]
