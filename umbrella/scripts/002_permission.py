import os
import sys

import django
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ObjectDoesNotExist

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()


def create_group_with_permission_ids(name, permission_ids=None):
    # Create a new group or get the existing one
    group, created = Group.objects.get_or_create(name=name)

    if permission_ids:
        # Get existing permissions of the group to avoid duplicates
        existing_permission_ids = set(group.permissions.values_list("id", flat=True))
        # Filter out the existing permission IDs from the new ones to prevent duplicates
        new_permissions = Permission.objects.filter(id__in=permission_ids).exclude(id__in=existing_permission_ids)

        if new_permissions.exists():
            group.permissions.add(*new_permissions)  # Only add new, non-duplicate permissions
            print(f"Added new permissions to the group '{name}'.")
        else:
            print(f"No new permissions added; group '{name}' already has all specified permissions.")

    group.save()
    return group


def add_user_to_group(username, group_name):
    try:
        user = User.objects.get(username=username)
        group = Group.objects.get(name=group_name)

        if group not in user.groups.all():
            user.groups.add(group)
            print(f"User {username} added to group {group_name} successfully.")
        else:
            print(f"User {username} is already in group {group_name}. No action taken.")
    except ObjectDoesNotExist as e:
        print(f"An error occurred: {e}")
        # Optionally, handle the error, e.g., by creating the user or group if they do not exist


def run():
    try:
        users = User.objects.all()
        user = users[len(users) - 1]
    except:
        print("Error: create some users first")
        sys.exit(1)
    # permission_ids = [1, 2, 3, 4]  # Assume these are valid permission IDs
    # create_group_with_permission_ids("Scientist", permission_ids)
    add_user_to_group(user, "Scientist")
    print("added last user to Scientist group")


if __name__ == "__main__":
    run()
