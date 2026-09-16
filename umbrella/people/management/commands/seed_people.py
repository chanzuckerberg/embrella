"""Fill the author directory so Add-author isn't empty.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from people.models import Person


class Command(BaseCommand):
    help = "Create a people.Person for each named active user missing one, so the author directory isn't empty."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        User = get_user_model()
        # Only named accounts with no directory entry yet — skips old/test logins that have no
        # first/last name (Person requires given/family). 
        users = (
            User.objects.filter(is_active=True, person__isnull=True)
            .exclude(first_name="")
            .exclude(last_name="")
            .order_by("id")
        )

        created = 0
        linked = 0
        for user in users.iterator():
            try:
                given = user.first_name.strip()
                family = user.last_name.strip()
                if not (given and family):
                    continue  # whitespace-only name — required fields must be real
                email = (user.email or "").strip()
                # If person already exists, link to them instead of making a copy.
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
                        self.stdout.write(f"would link: {existing} -> {user.get_username()}")
                    else:
                        existing.user = user
                        existing.save(update_fields=["user", "updated_at"])
                    linked += 1
                    continue

                if dry_run:
                    self.stdout.write(f"would create: {given} {family}{f' <{email}>' if email else ''}")
                else:
                    Person.objects.create(user=user, given_name=given, family_name=family, contact_email=email)
                created += 1
            except Exception as exc:  # noqa: BLE001 - one bad user must not abort the whole backfill
                self.stderr.write(self.style.WARNING(f"skipped {user.get_username()}: {exc}"))

        verb = "Would seed" if dry_run else "Seeded"
        suffix = " (dry run)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{verb} {created} created, {linked} linked{suffix}"))
