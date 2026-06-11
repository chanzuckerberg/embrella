# MariaDB for rootless-podman hosts on the native kernel overlay driver.
#
# Why this exists: the stock mariadb entrypoint, when it sees it's running as
# root, re-launches itself as the `mysql` user (UID 999) via `exec gosu` BEFORE
# mysqld starts. Rootless podman on the native overlay driver cannot exec
# a process as a non-root in-container UID
#
# Fix: neutralise that single re-exec so the entrypoint keeps running as the
# container's UID 0 which rootless podman updates with the host's UID.
FROM docker.io/library/mariadb:10.5.22

RUN set -eux; \
    grep -q 'exec gosu' /usr/local/bin/docker-entrypoint.sh; \
    sed -i '/exec gosu/c\true' /usr/local/bin/docker-entrypoint.sh; \
    ! grep -q 'exec gosu' /usr/local/bin/docker-entrypoint.sh
