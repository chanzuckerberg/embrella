# syntax=docker/dockerfile:1

# ---- deps stage: yarn install with cache ----
FROM node:24.16.0-slim AS deps

ENV YARN_ENABLE_GLOBAL_CACHE=false \
    YARN_ENABLE_TELEMETRY=false

WORKDIR /app

# corepack must run as root
RUN corepack enable && corepack prepare yarn@4.9.1 --activate
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# For devcontainer: reuse the base image's `node` user, matching uid `embrella` user for the devcontainer.
RUN chown node:node /app && mkdir -p /home/node/.yarn && chown -R node:node /home/node/.yarn

# Bring in the pinned yarn release from the repo
COPY --chown=node:node frontend/.yarn ./.yarn
COPY --chown=node:node frontend/.yarnrc.yml frontend/package.json frontend/yarn.lock ./

USER node
RUN --mount=type=cache,target=/app/.yarn/cache,uid=1000,gid=1000 yarn install --immutable

# ---- dev stage: full node_modules, seeds the frontend_node_modules volume ----
FROM deps AS dev

# ---- source stage: deps + app source, shared by `test` and `build` ----
FROM deps AS source
COPY --chown=node:node frontend/ ./

# ---- test stage: source without `yarn build` (jest / eslint / tsc / prettier) ----
FROM source AS test

# ---- build stage ----
FROM source AS build
RUN yarn build

# ---- runtime stage (prod): Next.js standalone output only ----
FROM node:24.16.0-slim AS runtime
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
