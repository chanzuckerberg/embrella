from django.contrib.auth.models import User, Group, Permission
import sys
import django
import os
from django.core.exceptions import ObjectDoesNotExist

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()

from django.contrib.auth.models import Group, Permission


def create_group_with_permission_ids(name, permission_ids=None):
    # Create a new group or get existing one
    group, created = Group.objects.get_or_create(name=name)

    if permission_ids:
        # `permission_ids` should be a list of IDs for the permissions
        permissions = Permission.objects.filter(id__in=permission_ids)  # Get permissions by their IDs
        group.permissions.set(permissions)  # Use set() to replace any existing permissions

    group.save()
    return group


def add_user_to_group(username, group_name):
    try:
        user = User.objects.get(username=username)
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
    except ObjectDoesNotExist as e:
        print(f"An error occurred: {e}")
        # Optionally, handle the error, e.g., by creating the user or group if they do not exist
    else:
        print(f"User {username} added to group {group_name} successfully.")


def run():
    permission_ids = [1, 2, 3, 4]  # Refer user auth auth permission table
    create_group_with_permission_ids("Scientist", permission_ids)
    add_user_to_group('test', 'Scientist')

if __name__ == "__main__":
    run()

