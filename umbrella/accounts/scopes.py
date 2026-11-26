"""What an API token may reach.

Two coarse scopes until object permissions land:

    embrella:read   GET / HEAD / OPTIONS
    embrella:write  any method

Some routes are never token-reachable, whatever the scope (DENIED_*).
"""

from enum import StrEnum

from django.conf import settings

EMBRELLA_AUDIENCE = "embrella"

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class Scope(StrEnum):
    READ = "embrella:read"
    WRITE = "embrella:write"


# Whole URL namespaces, e.g. every "admin:*" route
DENIED_NAMESPACES = frozenset({"admin"})

# Login, signup and SSO callbacks (allauth); matched on the view's module
DENIED_MODULES = ("allauth",)

# Individual routes, by resolved view_name
DENIED_VIEWS = frozenset(
    {
        "workflow:check_ssh_setup",  # takes a cluster password
        "workflow:setup_ssh_key",
    }
)

# Readable, but a token must not change them, e.g. add itself to a project
DENIED_WRITES = frozenset({"projects:project-members"})


def grantable_scopes() -> list[str]:
    """Embrella scopes plus extension scopes (TOKEN_EXTRA_SCOPES) that only other services check."""
    return [*Scope, *settings.TOKEN_EXTRA_SCOPES]


def allows(scopes, method: str) -> bool:
    if Scope.WRITE in scopes:
        return True
    return Scope.READ in scopes and method in READ_METHODS


def is_denied(match, method: str) -> bool:
    """True if the resolved route is off-limits to tokens."""
    if DENIED_NAMESPACES.intersection(match.namespaces):
        return True

    module = getattr(match.func, "__module__", "") or ""
    if module.startswith(DENIED_MODULES):
        return True

    if match.view_name in DENIED_VIEWS:
        return True

    return match.view_name in DENIED_WRITES and method not in READ_METHODS
