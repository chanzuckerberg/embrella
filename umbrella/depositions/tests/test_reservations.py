"""SigV4 signing behavior for LambdaReservationService."""

import json

import pytest
import requests
from botocore.credentials import Credentials
from botocore.exceptions import ProfileNotFound

from depositions.services.reservations import LambdaReservationService

BASE_URL = "https://abc123.lambda-url.us-west-2.on.aws"


def _fake_response(payload):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    response.headers["Content-Type"] = "application/json"
    return response


def _raise_profile_not_found(self):
    raise ProfileNotFound(profile="embrella")


@pytest.fixture
def captured(monkeypatch):
    """Capture the PreparedRequest the service sends, returning a canned reservation payload."""
    sent = {}

    def fake_send(self, prepared, **kwargs):
        sent["request"] = prepared
        return _fake_response({"deposition_id": 10001, "dataset_id": 20001})

    monkeypatch.setattr(requests.Session, "send", fake_send)
    return sent


def test_signs_request_with_region_from_url_and_covers_querystring(monkeypatch, captured):
    creds = Credentials(access_key="AKIAEXAMPLE", secret_key="secret", token=None)
    monkeypatch.setattr("botocore.session.Session.get_credentials", lambda self: creds)

    LambdaReservationService(BASE_URL).list_reservations(detail=True)

    request = captured["request"]
    assert request.url.endswith("/reservations?detail=true")
    auth = request.headers["Authorization"]
    assert auth.startswith("AWS4-HMAC-SHA256")
    assert "/us-west-2/lambda/aws4_request" in auth


@pytest.mark.parametrize(
    "get_credentials",
    [lambda self: None, _raise_profile_not_found],
    ids=["no-credentials", "missing-profile"],
)
def test_unsigned_when_credentials_unavailable(monkeypatch, captured, get_credentials):
    # No credentials, or a stray AWS_PROFILE pointing at a missing profile: unsigned, no 500.
    monkeypatch.setattr("botocore.session.Session.get_credentials", get_credentials)

    assert LambdaReservationService(BASE_URL).reserve_new_dataset() == 20001
    assert "Authorization" not in captured["request"].headers


def test_non_function_url_is_unsigned_without_credential_lookup(monkeypatch, captured):
    # A non-Lambda host (e.g. a local mock) must not trigger credential discovery at all.
    def must_not_run(self):
        raise AssertionError("get_credentials should not run for a non-Function-URL host")

    monkeypatch.setattr("botocore.session.Session.get_credentials", must_not_run)

    assert LambdaReservationService("http://localhost:8000").reserve_new_deposition() == 10001
    assert "Authorization" not in captured["request"].headers
