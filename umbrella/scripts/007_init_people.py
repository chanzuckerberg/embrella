"""Seed the people directory with example institutions and people.

Dev-only example data, run via ``manage.py runscript 007_init_people`` (or
``just populatedbexamples``). Idempotent: re-running updates the same rows
rather than creating duplicates, keyed by ROR id / ORCID where available.

The figures below are well-known scientists used as placeholders — substitute
real entries later. They intentionally cover the edge cases the API handles:
people with and without an ORCID, and people with and without an institution.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()

from people.models import Institution, Person

INSTITUTIONS = [
    {"name": "Biohub", "ror_id": "00knt4f32", "city": "Redwood City", "country": "USA", "address": "3400 Bridge Pkwy"},
]

# (orcid, given, family, contact_email, institution_name)
# orcid=None and institution_name=None exercise the nullable paths.
PEOPLE = [
    ("0000-0003-0192-307X", "David", "Dong", "david.dong@biohub.org", "Biohub"),
]


def run():
    institutions = {}
    for spec in INSTITUTIONS:
        institution, _ = Institution.objects.update_or_create(
            ror_id=spec["ror_id"],
            defaults={k: v for k, v in spec.items() if k != "ror_id"},
        )
        institutions[institution.name] = institution

    for orcid, given, family, email, institution_name in PEOPLE:
        if institution_name is not None and institution_name not in institutions:
            # Catch a stale/typo'd name during substitution instead of silently
            # seeding the person with no institution.
            raise KeyError(
                f"{given} {family} references unknown institution {institution_name!r}; known: {sorted(institutions)}"
            )
        defaults = {
            "given_name": given,
            "family_name": family,
            "contact_email": email,
            "institution": institutions.get(institution_name),
        }
        if orcid is not None:
            # Key on ORCID when present so re-runs update the same row.
            Person.objects.update_or_create(orcid=orcid, defaults=defaults)
        else:
            # No ORCID to dedupe on; fall back to name so re-runs stay idempotent.
            Person.objects.update_or_create(orcid=None, given_name=given, family_name=family, defaults=defaults)

    print(f"Seeded {Institution.objects.count()} institutions and {Person.objects.count()} people.")


if __name__ == "__main__":
    run()
