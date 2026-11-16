"""Reservation service for deposition + dataset IDs."""

import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict
from urllib.parse import urlsplit

import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# Function URLs look like <id>.lambda-url.<region>.on.aws - the host carries the signing region.
_FUNCTION_URL_REGION = re.compile(r"\.lambda-url\.([a-z0-9-]+)\.on\.aws$")


class ReservationService(ABC):
    """Abstract interface for reservation backends."""

    @abstractmethod
    def reserve_new_deposition(self) -> int: ...

    @abstractmethod
    def reserve_new_dataset(self) -> int: ...

    @abstractmethod
    def validate_deposition(self, deposition_id: int) -> Dict[str, Any]:
        """Check if a deposition ID is reserved.
        Returns dict with keys: deposition_id, instantiated, reservation.
        """

    @abstractmethod
    def validate_dataset(self, dataset_id: int) -> Dict[str, Any]:
        """Check if a dataset ID is reserved.
        Returns dict with keys: dataset_id, instantiated, reservation.
        """

    @abstractmethod
    def list_reservations(self, detail: bool = False) -> Dict[str, Any]:
        """List reservations. If detail=True, includes full datasets/depositions dicts."""


class StubReservationService(ReservationService):
    """In-memory stub for local dev. Class-level counters from 10000; reset on process restart."""

    _next_deposition_id = 10000
    _next_dataset_id = 10000

    def reserve_new_deposition(self) -> int:
        StubReservationService._next_deposition_id += 1
        return StubReservationService._next_deposition_id

    def reserve_new_dataset(self) -> int:
        StubReservationService._next_dataset_id += 1
        return StubReservationService._next_dataset_id

    def validate_deposition(self, deposition_id: int) -> Dict[str, Any]:
        return {
            "deposition_id": deposition_id,
            "instantiated": deposition_id <= StubReservationService._next_deposition_id,
            "reservation": {},
        }

    def validate_dataset(self, dataset_id: int) -> Dict[str, Any]:
        return {
            "dataset_id": dataset_id,
            "instantiated": dataset_id <= StubReservationService._next_dataset_id,
            "reservation": {},
        }

    def list_reservations(self, detail: bool = False) -> Dict[str, Any]:
        response: Dict[str, Any] = {
            "next_deposition_id": StubReservationService._next_deposition_id + 1,
            "next_dataset_id": StubReservationService._next_dataset_id + 1,
            "dataset_count": 0,
            "deposition_count": 0,
        }
        if detail:
            response["datasets"] = {}
            response["depositions"] = {}
        return response


class LambdaReservationService(ReservationService):
    """HTTPS client for the reservation lambda; Function URLs require AWS credentials."""

    DEFAULT_TIMEOUT_SECONDS = 30

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _sigv4_headers(self, url: str) -> Dict[str, str]:
        """Sign a Function URL GET; leave other hosts unsigned."""
        # Only Function URLs are signed; skip credential discovery otherwise.
        region = _FUNCTION_URL_REGION.search(urlsplit(url).hostname or "")
        if region is None:
            return {}
        credentials = Session().get_credentials()
        if credentials is None:
            raise RuntimeError("AWS credentials are required for reservation calls.")
        request = AWSRequest(method="GET", url=url)
        SigV4Auth(credentials, "lambda", region.group(1)).add_auth(request)
        return dict(request.headers)

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        # Prepare the full URL (incl. querystring) first so the signature covers it.
        prepared = requests.Request("GET", f"{self.base_url}{path}", params=params).prepare()
        prepared.headers.update(self._sigv4_headers(prepared.url))
        with requests.Session() as session:
            response = session.send(prepared, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def reserve_new_deposition(self) -> int:
        return self._get("/reservations/deposition/new")["deposition_id"]

    def reserve_new_dataset(self) -> int:
        return self._get("/reservations/dataset/new")["dataset_id"]

    def validate_deposition(self, deposition_id: int) -> Dict[str, Any]:
        return self._get(f"/reservations/deposition/{deposition_id}")

    def validate_dataset(self, dataset_id: int) -> Dict[str, Any]:
        return self._get(f"/reservations/dataset/{dataset_id}")

    def list_reservations(self, detail: bool = False) -> Dict[str, Any]:
        params = {"detail": "true"} if detail else None
        return self._get("/reservations", params=params)


def get_reservation_service() -> ReservationService:
    """Factory: RESERVATION_LAMBDA_URL set → lambda client; else the in-memory stub (local dev only)."""
    lambda_url = os.environ.get("RESERVATION_LAMBDA_URL", "").strip()
    if lambda_url:
        return LambdaReservationService(lambda_url)
    # The stub's IDs reset on restart and aren't shared across workers, so they can collide with real ones.
    if settings.DEBUG:
        return StubReservationService()
    raise ImproperlyConfigured(
        "RESERVATION_LAMBDA_URL is not set; refusing to hand out in-memory reservation IDs outside local dev."
    )
