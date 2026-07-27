#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def _maybe_start_debugpy():
    # Set DEBUGPY_LISTEN=1 (typically in compose.dev.yaml) to open a debugpy
    # socket on DEBUGPY_PORT (default 5678) so VS Code / PyCharm can attach.
    if os.environ.get("DEBUGPY_LISTEN") != "1":
        return
    # Django's runserver autoreloader spawns a child process to serve requests
    # and sets RUN_MAIN="true" in it. We want debugpy in the child, not the
    # parent (which only watches files). For non-runserver invocations
    # (qcluster, gunicorn, manage.py shell), RUN_MAIN is unset and we listen.
    run_main = os.environ.get("RUN_MAIN")
    if run_main is not None and run_main != "true":
        return
    try:
        import debugpy
    except ImportError:
        return
    port = int(os.environ.get("DEBUGPY_PORT", "5678"))
    try:
        debugpy.listen(("0.0.0.0", port))
    except (OSError, RuntimeError):
        pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
    _maybe_start_debugpy()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?",
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
