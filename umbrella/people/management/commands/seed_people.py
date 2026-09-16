"""Fill the author directory so Add-author isn't empty.

For each active user with no Person yet: link an existing unlinked Person with
the same email if there is one, otherwise create a new one. Safe to re-run.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from people.models import Person


class Command(BaseCommand):
    help = "Create a people.Person for each active user missing one, so the author directory isn't empty."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        User = get_user_model()
        # Active users who don't have a directory entry yet.
        users = User.objects.filter(is_active=True, person__isnull=True).order_by("id")

        created = 0
        linked = 0
        for user in users.iterator():
            username = user.get_username()
            try:
                # Older accounts might have a blank User.email but an email-shaped username.
                email = (user.email or "").strip() or (username.strip() if "@" in username else "")
                # If person exists, link to them instead of making a copy.
                # Skip blank emails so we don't grab the wrong one.
                existing = None
                if email:
                    matches = list(Person.objects.filter(user__isnull=True, contact_email__iexact=email).order_by("id"))
                    if len(matches) > 1:
                        self.stderr.write(
                            self.style.WARNING(f"{len(matches)} unlinked people share {email}; linking the oldest")
                        )
                    existing = matches[0] if matches else None
                if existing:
                    if dry_run:
                        self.stdout.write(f"would link: {existing} -> {username}")
                    else:
                        existing.user = user
                        existing.save(update_fields=["user", "updated_at"])
                    linked += 1
                    continue

                # Use the username when there's no name.
                given = (user.first_name or "").strip() or username
                family = (user.last_name or "").strip()
                if dry_run:
                    label = " ".join(p for p in (given, family) if p)
                    self.stdout.write(f"would create: {label}{f' <{email}>' if email else ''}")
                else:
                    Person.objects.create(user=user, given_name=given, family_name=family, contact_email=email)
                created += 1
            except Exception as exc:  # noqa: BLE001 - one bad user must not abort the whole backfill
                self.stderr.write(self.style.WARNING(f"skipped {username}: {exc}"))

        verb = "Would seed" if dry_run else "Seeded"
        suffix = " (dry run)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{verb} {created} created, {linked} linked{suffix}"))
