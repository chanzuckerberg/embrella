import pytest
from django.contrib.auth.models import User

from accounts.bots import create_bot


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="alice", password="pw")


@pytest.fixture
def bot(owner):
    return create_bot(owner, "bot-hydra-1", "Hydra 1")


@pytest.fixture
def staff(owner, client):
    """``client`` logged in as ``owner``, promoted to superuser for the admin."""
    owner.is_staff = owner.is_superuser = True
    owner.save()
    client.force_login(owner)
    return client
