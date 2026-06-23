from functools import lru_cache


class MissingClusterCredentialsError(Exception):
    """No UserClusterCredentials row exists for (user, cluster).

    Per-user clusterio callers should catch this and surface the standard
    ssh_setup_required 403 contract so the frontend opens the SSH setup modal.
    """

    def __init__(self, user_pk, cluster_id):
        self.user_pk = user_pk
        self.cluster_id = cluster_id
        super().__init__(
            f"No cluster credentials for user pk={user_pk} on cluster '{cluster_id}'",
        )


@lru_cache(maxsize=512)
def _lookup_username(user_pk, cluster_id):
    """Cached lookup of UserClusterCredentials.username by user pk + cluster id.

    lru_cache does not cache exceptions, so a None sentinel signals "no row";
    callers raise MissingClusterCredentialsError on None.
    """
    from .models import UserClusterCredentials
    row = (
        UserClusterCredentials.objects
        .filter(user_id=user_pk, cluster_id=cluster_id)
        .values_list("username", flat=True)
        .first()
    )
    return row


def clear_username_cache():
    """Invalidate the in-process credentials lookup cache.

    Called from post_save/post_delete signals on UserClusterCredentials.
    """
    _lookup_username.cache_clear()


def resolve_cluster_username(user, cluster_id):
    """Return the cluster-side SSH username for `user` on `cluster_id`.

    Raises MissingClusterCredentialsError if the user has not set up
    credentials for that cluster — callers should catch and route the user
    through the SSH setup flow.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        raise MissingClusterCredentialsError(getattr(user, "pk", None), cluster_id)
    username = _lookup_username(user.pk, cluster_id)
    if username is None:
        raise MissingClusterCredentialsError(user.pk, cluster_id)
    return username


def format_cluster_username_for_display(user, cluster_id):
    """Display-side wrapper around resolve_cluster_username.

    Returns an empty string when credentials aren't set up so list views and
    tables don't break — UI code decides how to render the empty case
    (e.g. a "Not configured" badge).
    """
    try:
        return resolve_cluster_username(user, cluster_id)
    except MissingClusterCredentialsError:
        return ""
