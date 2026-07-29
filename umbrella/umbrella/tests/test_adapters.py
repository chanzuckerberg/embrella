"""Tests for the allauth adapters: username generation and SSO domain gating."""

import pytest
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth.models import User

from umbrella.adapters import UmbrellaAccountAdapter, UmbrellaSocialAccountAdapter


def _populate(first_name="", last_name="", email=""):
    adapter = UmbrellaAccountAdapter()
    user = User(first_name=first_name, last_name=last_name, email=email)
    adapter.populate_username(request=None, user=user)
    return user.username


@pytest.mark.django_db
class TestPopulateUsername:
    def test_first_and_last_name(self):
        # allauth normalizes candidates to lowercase ASCII.
        assert _populate("Test", "Me", "Test.Me@example.com") == "test.me"

    def test_collision_gets_suffix(self):
        User.objects.create(username="test.me")
        username = _populate("Test", "Me", "Test.Me@example.com")
        assert username != "test.me"
        assert username.startswith("test.me")

    def test_missing_last_name_falls_back_to_email_local_part(self):
        assert _populate("Test", "", "this.part@example.com") == "this.part"

    def test_no_names_falls_back_to_email_local_part(self):
        assert _populate("", "", "this.part@example.com") == "this.part"

    def test_existing_username_preserved(self):
        adapter = UmbrellaAccountAdapter()
        user = User(username="preset", first_name="Test", last_name="Me")
        adapter.populate_username(request=None, user=user)
        assert user.username == "preset"


class _FakeSocialLogin:
    """Minimal stand-in — pre_social_login only reads the email off these two."""

    def __init__(self, email="", extra_email=None):
        self.user = User(email=email)
        self.account = type("account", (), {"extra_data": {"email": extra_email} if extra_email else {}})()


class TestSocialLoginDomainGate:
    CZI_DOMAINS = ["czii.org", "czbiohub.org", "biohub.org"]

    def _login(self, email, extra_email=None):
        UmbrellaSocialAccountAdapter().pre_social_login(request=None, sociallogin=_FakeSocialLogin(email, extra_email))

    def test_allowed_domain_passes(self, settings):
        settings.SSO_ALLOWED_DOMAINS = self.CZI_DOMAINS
        self._login("someone@czii.org")

    def test_email_from_extra_data_is_used(self, settings):
        settings.SSO_ALLOWED_DOMAINS = self.CZI_DOMAINS
        self._login("", extra_email="someone@czbiohub.org")

    def test_disallowed_domain_rejected(self, settings):
        settings.SSO_ALLOWED_DOMAINS = self.CZI_DOMAINS
        with pytest.raises(ImmediateHttpResponse):
            self._login("someone@gmail.com")

    def test_wildcard_admits_any_domain(self, settings):
        settings.SSO_ALLOWED_DOMAINS = ["*"]
        self._login("someone@gmail.com")

    @pytest.mark.parametrize("email", ["", "not-an-email"])
    def test_wildcard_still_requires_a_usable_email(self, settings, email):
        settings.SSO_ALLOWED_DOMAINS = ["*"]
        with pytest.raises(ImmediateHttpResponse):
            self._login(email)
