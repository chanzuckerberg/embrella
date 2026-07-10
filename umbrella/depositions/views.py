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

from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
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
    SubmissionDepositionSerializer,
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


@extend_schema_view(
    create=extend_schema(
        summary="Create a deposition",
        description="Creates a deposition draft. `deposition_id` is reserved server-side; "
                    "`submitter_user` is set from the request — don't send them.",
        examples=[OpenApiExample(
            "New deposition",
            request_only=True,
            value={
                "title": "In situ cryo-ET of bacterial cells",
                "description": "Tomograms of whole cells imaged by cryo-ET.",
                "deposition_publications": "https://doi.org/10.1234/example",
                "related_database_entries": "EMPIAR-12345, EMD-67890",
                "authors_json": [
                    {"author_id": 1, "author_list_order": 1, "is_primary": True, "is_corresponding": True},
                    {"author_id": 2, "author_list_order": 2, "is_primary": False, "is_corresponding": False},
                ],
                "release_date": "2026-12-01",
            },
        )],
    ),
    partial_update=extend_schema(
        summary="Update a deposition",
        examples=[OpenApiExample(
            "Patch fields",
            request_only=True,
            value={"description": "Updated description.", "release_date": "2027-01-15"},
        )],
    ),
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
        # My Submissions list: lean per-deposition rows with session names + derived type.
        # Prefetch sessions -> msi_session (names) + annotations (type) to avoid N+1.
        queryset = self.filter_queryset(self.get_queryset()).prefetch_related(
            "datasets__sessions__msi_session",
            "datasets__sessions__annotations",
            "datasets__sessions__tiltseries_metadata",
            "datasets__sessions__tomogram_metadata",
        )
        serializer = SubmissionDepositionSerializer(queryset, many=True)
        return Response({"submissions": serializer.data, "total_count": queryset.count()})


@extend_schema_view(
    create=extend_schema(
        summary="Create a dataset",
        description="Create a dataset under a deposition. Pass the deposition's `id` (from its "
                    "create response) as `deposition` — not the `deposition_id`. `dataset_id` "
                    "and `status` are set for you.",
        examples=[OpenApiExample(
            "New dataset",
            request_only=True,
            value={
                "deposition": 1,
                "title": "Dataset 1 — strain ABC",
                "description": "Single-axis tilt series, 3.0 A/px.",
                "sample_preparation": "Plunge-frozen on Quantifoil grids.",
                "grid_preparation": "Glow-discharged 30 s.",
                "assay_label": "cryo-electron tomography",
                "assay_ontology_id": "EFO:0010961",
            },
        )],
    ),
    partial_update=extend_schema(
        summary="Update a dataset (fields + nested funding / sessions)",
        description="Nested `funding` and `sessions` are FULL-REPLACE: any row omitted from the "
                    "array is deleted. Each session entry must include `msi_session` (the MsiSession's id).",
        examples=[OpenApiExample(
            "Patch with funding + sessions",
            request_only=True,
            value={
                "description": "Updated experimental notes.",
                "funding": [
                    {"funding_agency_name": "Chan Zuckerberg Initiative", "grant_id": "CZI-2026-001"},
                    {"funding_agency_name": "NIH", "grant_id": "R01-GM-123456"},
                ],
                "sessions": [
                    {
                        "msi_session": 42,
                        "aretomo_run_name": "run001",
                        "denoise_run_name": "",
                        "selected_copick_runs": [],
                    },
                ],
            },
        )],
    ),
)
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


@extend_schema_view(
    partial_update=extend_schema(
        summary="Save a session (metadata + annotations)",
        description="Saves session metadata and copick annotations in one PATCH. `annotations` "
                    "upsert by (copick_kind, copick_ref) and are full-replace — any omitted is "
                    "removed. Method links are managed via their own endpoint.",
        examples=[OpenApiExample(
            "Save metadata + annotations",
            request_only=True,
            value={
                "tiltseries_metadata": {
                    "acceleration_voltage": 300, "pixel_spacing": 1.5,
                    "tilt_min": -60, "tilt_max": 60, "tilt_step": 3,
                },
                "tomogram_metadata": {
                    "voxel_spacing": 7.84, "reconstruction_method": "WBP", "ctf_corrected": True,
                },
                "annotations": [
                    {
                        "copick_kind": "picks", "copick_ref": "ribosome-0",
                        "object_name": "ribosome", "object_count": 1200,
                        "method_type": "automated", "is_selected": True,
                    },
                ],
            },
        )],
    ),
)
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


@extend_schema_view(
    create=extend_schema(
        summary="Add a method link to an annotation",
        description="`annotation` is the annotation's `id`. `link_type` is one of: "
                    "documentation / models_weights / other / source_code / website.",
        examples=[OpenApiExample(
            "New method link",
            request_only=True,
            value={
                "annotation": 1,
                "link_type": "source_code",
                "link": "https://github.com/example/picking-model",
                "custom_name": "Picking model repo",
            },
        )],
    ),
)
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
