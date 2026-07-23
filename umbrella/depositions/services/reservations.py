"""Reservation service for deposition + dataset IDs."""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict

import requests


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
    """HTTPS client for the cryoet-data-portal reservation lambda (RESERVATION_LAMBDA_URL)."""

    DEFAULT_TIMEOUT_SECONDS = 30

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout,
        )
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
    """Factory: RESERVATION_LAMBDA_URL set → lambda client; else stub (local dev)."""
    lambda_url = os.environ.get("RESERVATION_LAMBDA_URL", "").strip()
    if lambda_url:
        return LambdaReservationService(lambda_url)
    return StubReservationService()
