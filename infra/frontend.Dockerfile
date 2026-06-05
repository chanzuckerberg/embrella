# syntax=docker/dockerfile:1

# ---- deps stage: yarn install with cache ----
FROM node:20.16.0-slim AS deps

ENV YARN_ENABLE_GLOBAL_CACHE=false \
    YARN_ENABLE_TELEMETRY=false

WORKDIR /app

# corepack must run as root (writes shims under /usr/local/bin).
RUN corepack enable && corepack prepare yarn@4.9.1 --activate
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# Reuse the base image's `node` user so files in /app and the
# shared `frontend_node_modules` / `frontend_next` named volumes are owned
# by uid 1000 — matching the backend's `embrella` user for the devcontainer.
RUN chown node:node /app && mkdir -p /home/node/.yarn && chown -R node:node /home/node/.yarn

# Bring in the pinned yarn release from the repo
COPY --chown=node:node frontend/.yarn ./.yarn
COPY --chown=node:node frontend/.yarnrc.yml frontend/package.json frontend/yarn.lock ./

RUN yarn install --immutable

# ---- build stage ----
FROM deps AS build
COPY --chown=node:node frontend/ ./
RUN yarn build

# ---- runtime stage (prod) ----
FROM node:20.16.0-slim AS runtime
ENV NODE_ENV=production \
    YARN_ENABLE_TELEMETRY=false
WORKDIR /app
RUN corepack enable && corepack prepare yarn@4.9.1 --activate
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
COPY --from=build --chown=node:node /app ./
USER node
EXPOSE 3000
CMD ["yarn", "start"]
