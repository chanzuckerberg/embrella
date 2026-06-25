"""DRF viewsets for the depositions app.

  DepositionViewSet  -> /depositions/v1/depositions/   (container CRUD)
  DatasetViewSet     -> /depositions/v1/datasets/      (submit unit CRUD + actions)
  DepositionSessionViewSet -> /depositions/v1/sessions/  (session detail save + actions)
  MethodLinkViewSet  -> /depositions/v1/method-links/  (+ nested create under an annotation)

IDs are reserved from the ReservationService on create. Action endpoints that depend on
the processors / auto-fill service (submit, job-status, logs, config.yaml, auto-fill,
subset-csv) are stubbed with 501 until those in place.
"""

import logging

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Dataset,
    Deposition,
    DepositionAnnotationMethodLink,
    DepositionSession,
)
from .serializers import (
    DatasetSerializer,
    DepositionAnnotationMethodLinkSerializer,
    DepositionSerializer,
    DepositionSessionSerializer,
)
from .services import get_reservation_service

logger = logging.getLogger(__name__)

# Intentionally do not support PUT (full-replace). The wizard autosaves
# partial updates step by step, so updates go through PATCH only.
HTTP_METHODS_NO_PUT = ["get", "post", "patch", "delete", "head", "options"]


def _not_implemented():
    return Response(
        {"detail": "Not implemented yet - lands with the processor/auto-fill."},
        status=status.HTTP_501_NOT_IMPLEMENTED,
    )


class DepositionViewSet(viewsets.ModelViewSet):
    """Container CRUD. list returns depositions with datasets nested (My Submissions)."""

    permission_classes = [IsAuthenticated]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DepositionSerializer
    queryset = Deposition.objects.all().prefetch_related("datasets", "datasets__funding", "datasets__sessions", "datasets__job")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if self.request.query_params.get("scope") == "mine":
            return qs.filter(submitter_user=user)
        # default visibility — TODO: confirm All-vs-Mine product decision
        return qs.filter(submitter_user=user)

    def perform_create(self, serializer):
        deposition_id = None
        try:
            deposition_id = get_reservation_service().reserve_new_deposition()
        except Exception:
            logger.exception("Failed to reserve deposition id; saving draft without one")
        serializer.save(submitter_user=self.request.user, deposition_id=deposition_id)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({"submissions": serializer.data, "total_count": queryset.count()})


class DatasetViewSet(viewsets.ModelViewSet):
    """Submit unit CRUD + per-dataset actions."""

    permission_classes = [IsAuthenticated]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DatasetSerializer
    queryset = (
        Dataset.objects.all()
        .select_related("deposition", "job")
        .prefetch_related("funding", "sessions")
    )

    def get_queryset(self):
        qs = super().get_queryset().filter(deposition__submitter_user=self.request.user)
        deposition_id = self.request.query_params.get("deposition")
        if deposition_id:
            qs = qs.filter(deposition_id=deposition_id)
        return qs

    def perform_create(self, serializer):
        dataset_id = None
        try:
            dataset_id = get_reservation_service().reserve_new_dataset()
        except Exception:
            logger.exception("Failed to reserve dataset id; saving without one")
        serializer.save(dataset_id=dataset_id)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return _not_implemented()  # TODO: trigger DepositionPrepProcessor (per dataset)

    @action(detail=True, methods=["get"], url_path="job-status")
    def job_status(self, request, pk=None):
        return _not_implemented()  # TODO: read DatasetJob state

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        return _not_implemented()  # TODO: fetch_job_logs

    @action(detail=True, methods=["get"], url_path="config.yaml")
    def config_yaml(self, request, pk=None):
        return _not_implemented()  # TODO: config_yaml serializer


class DepositionSessionViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Session detail save (metadata + annotations) + per-session actions.

    No create/list/delete — sessions are selected/removed via the dataset's nested
    `sessions`, and read via the deposition tree.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DepositionSessionSerializer
    queryset = DepositionSession.objects.all().select_related("dataset__deposition")

    def get_queryset(self):
        return super().get_queryset().filter(
            dataset__deposition__submitter_user=self.request.user
        )

    @action(detail=True, methods=["post"], url_path="auto-fill")
    def auto_fill(self, request, pk=None):
        return _not_implemented()  # TODO: auto-fill service (cryoetportalprep init via SSH)

    @action(detail=True, methods=["post"], url_path="subset-csv")
    def subset_csv(self, request, pk=None):
        return _not_implemented()  # TODO: SCP subset CSV to cluster


class MethodLinkViewSet(viewsets.ModelViewSet):
    """CRUD for annotation method links (kept out of nested writes)."""

    permission_classes = [IsAuthenticated]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DepositionAnnotationMethodLinkSerializer
    queryset = DepositionAnnotationMethodLink.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(
            annotation__session__dataset__deposition__submitter_user=self.request.user
        )
