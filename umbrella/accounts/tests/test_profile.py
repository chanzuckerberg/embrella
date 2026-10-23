"""Tests for accounts.Profile and its auto-creation signal."""

import pytest
from django.contrib.auth.models import User

from accounts.models import Profile


@pytest.mark.django_db
class TestProfileAutoCreation:
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username="alice@example.com")
        assert Profile.objects.filter(user=user).exists()

    def test_no_duplicate_profile_on_user_save(self):
        user = User.objects.create_user(username="bob@example.com")
        user.email = "bob@example.com"
        user.save()
        assert Profile.objects.filter(user=user).count() == 1
