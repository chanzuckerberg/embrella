"""Bookkeeping for the `users` -> `accounts` app rename.

The physical table is pinned (`Meta.db_table = "users_userclustercredentials"`),
so this migration performs **no schema change**. It only repairs the Django
bookkeeping rows that key off the app *label*, so admin grouping, permissions,
and migration history stay consistent after the rename.

No manual pre-step is required. On existing staging/prod DBs the table was
created under the old `users` label, but `accounts.0001_initial` is now
idempotent (it no-ops when the pinned table already exists), so the executor
applies it cleanly and records an `accounts.0001_initial` history row itself.
This migration then:

- relabels the `users` content type to `accounts` (permissions follow their
  content type via `content_type_id`, so fixing the content type is enough), and
- deletes the orphaned `users.*` rows from `django_migrations` — the matching
  `accounts.*` rows are written naturally as each accounts migration applies, so
  renaming the old rows would create duplicate `(app, name)` records instead.

Fresh DBs: there are no `users` content types or history rows, so both steps
update/delete zero rows and are safe no-ops.
"""

from django.db import migrations


def rename_users_to_accounts(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="users").update(app_label="accounts")

    # Drop the orphaned migration-history rows for the old `users` label. The
    # `accounts.*` rows already exist (written by the executor as each accounts
    # migration applies), so we delete rather than rename to avoid duplicates.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DELETE FROM django_migrations WHERE app = %s", ["users"])


def rename_accounts_to_users(apps, schema_editor):
    # Best-effort reverse: relabel the content type back. The deleted history
    # rows are not recreated (the `accounts.*` rows remain and are removed by the
    # framework when these migrations are unapplied).
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="accounts").update(app_label="users")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(rename_users_to_accounts, rename_accounts_to_users),
    ]
