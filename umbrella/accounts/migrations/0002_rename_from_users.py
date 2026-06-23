"""Bookkeeping for the `users` -> `accounts` app rename.

The physical table is pinned (`Meta.db_table = "users_userclustercredentials"`),
so this migration performs **no schema change**. It only repairs the Django
bookkeeping rows that key off the app *label*, so admin grouping, permissions,
and migration history stay consistent after the rename.

Fresh DBs: there are no leftover `users` rows, so every statement here updates
zero rows and is a safe no-op.

Existing staging/prod DBs: the migration recorder (`django_migrations`) still has
`users.0001_initial` recorded as applied, while INSTALLED_APPS now only knows
`accounts`. Django would therefore try to re-apply `accounts.0001_initial`
(CreateModel) and fail because the pinned table already exists. To avoid that,
run this one-time SQL **before** `migrate` so the executor sees 0001 as applied:

    UPDATE django_migrations SET app = 'accounts'
      WHERE app = 'users' AND name = '0001_initial';

After that pre-step, `migrate` reaches this migration, which fixes the remaining
content-type / permission rows below (permissions follow their content type via
`content_type_id`, so updating the content type's `app_label` is sufficient).
"""

from django.db import migrations


def rename_users_to_accounts(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="users").update(app_label="accounts")

    # Idempotent safety net: also fix the migration-history row in case the
    # documented pre-step SQL was not run (no-op on fresh/already-fixed DBs).
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE django_migrations SET app = %s WHERE app = %s",
            ["accounts", "users"],
        )


def rename_accounts_to_users(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="accounts").update(app_label="users")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "UPDATE django_migrations SET app = %s WHERE app = %s",
            ["users", "accounts"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(rename_users_to_accounts, rename_accounts_to_users),
    ]
