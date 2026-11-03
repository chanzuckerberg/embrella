"""SigV4 signing behavior for LambdaReservationService."""

import json

import pytest
import requests
from botocore.credentials import Credentials

from depositions.services.reservations import LambdaReservationService

BASE_URL = "https://abc123.lambda-url.us-west-2.on.aws"


def _fake_response(payload):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    response.headers["Content-Type"] = "application/json"
    return response


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


def test_missing_credentials_fail_before_sending_request(monkeypatch, captured):
    monkeypatch.setattr("botocore.session.Session.get_credentials", lambda self: None)

    with pytest.raises(RuntimeError, match="AWS credentials are required for reservation calls"):
        LambdaReservationService(BASE_URL).reserve_new_dataset()
    assert "request" not in captured


def test_non_function_url_is_unsigned_without_credential_lookup(monkeypatch, captured):
    # A non-Lambda host (e.g. a local mock) must not trigger credential discovery at all.
    def must_not_run(self):
        raise AssertionError("get_credentials should not run for a non-Function-URL host")

    monkeypatch.setattr("botocore.session.Session.get_credentials", must_not_run)

    assert LambdaReservationService("http://localhost:8000").reserve_new_deposition() == 10001
    assert "Authorization" not in captured["request"].headers
