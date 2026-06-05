# MariaDB for rootless-podman hosts on the native kernel overlay driver.
#
# Why this exists: the stock mariadb entrypoint, when it sees it's running as
# root, re-launches itself as the `mysql` user (UID 999) via `exec gosu` BEFORE
# mysqld starts. Rootless podman on the native overlay driver cannot exec
# a process as a non-root in-container UID ("exec ... : Permission denied"), so
# the container dies on startup. There is no env var / flag to disable the drop.
#
# Fix: neutralise that single re-exec so the entrypoint keeps running as the
# container's UID 0 (which maps to the unprivileged host user under rootless
# podman), and run mariadbd itself with `--user=root` (set in the compose
# overlays). Everything else about the official image is unchanged.
FROM docker.io/library/mariadb:10.5.22

# Neutralise the privilege-drop re-exec.
RUN set -eux; \
    grep -Eq 'exec gosu .*"\$BASH_SOURCE"' /usr/local/bin/docker-entrypoint.sh; \
    sed -i -E '/exec gosu .*"\$BASH_SOURCE"/c\true' /usr/local/bin/docker-entrypoint.sh; \
    ! grep -Eq 'exec gosu .*"\$BASH_SOURCE"' /usr/local/bin/docker-entrypoint.sh
