import csv
import io
import json
import logging
import os
import time

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from processes.services.cluster_resolver import cluster_id_for_run
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from stores.models import Cluster, resolve_review_path

from .models import (
    Dataset,
    Deposition,
    DepositionSession,
    TiltseriesMetadata,
    TomogramMetadata,
)
from .permissions import IsDepositionOwnerOrReadOnly
from .serializers import (
    DatasetSerializer,
    DepositionSerializer,
    DepositionSessionSerializer,
    SubmissionDepositionSerializer,
)
from .services import get_reservation_service
from .services.autofill import (
    map_session_plan_to_instrument_metadata,
    map_session_to_metadata,
    run_autofill_init,
)
from .services.exceptions import SubmissionValidationError

logger = logging.getLogger(__name__)

DEPOSITION_DEFAULT_CLUSTER_ID = "bruno"


# Wizard autosaves via PATCH only — no PUT full-replace.
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
        examples=[
            OpenApiExample(
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
            )
        ],
    ),
    partial_update=extend_schema(
        summary="Update a deposition",
        examples=[
            OpenApiExample(
                "Patch fields",
                request_only=True,
                value={"description": "Updated description.", "release_date": "2027-01-15"},
            )
        ],
    ),
)
class DepositionViewSet(viewsets.ModelViewSet):
    """Container CRUD; list nests datasets (My Submissions)."""

    permission_classes = [IsAuthenticated, IsDepositionOwnerOrReadOnly]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DepositionSerializer
    queryset = Deposition.objects.all().prefetch_related(
        "datasets", "datasets__funding", "datasets__sessions", "datasets__job"
    )

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("scope") == "mine":
            qs = qs.filter(submitter_user=self.request.user)
        if self.action == "retrieve":
            qs = qs.prefetch_related("datasets__sessions__annotations__method_links")
        return qs

    def perform_create(self, serializer):
        deposition_id = None
        try:
            deposition_id = get_reservation_service().reserve_new_deposition()
        except Exception:
            logger.exception("Failed to reserve deposition id; saving draft without one")
        serializer.save(submitter_user=self.request.user, deposition_id=deposition_id)

    def list(self, request, *args, **kwargs):
        # Lean list rows; prefetch sessions/annotations to avoid N+1.
        queryset = self.filter_queryset(self.get_queryset()).prefetch_related(
            "datasets__sessions__msi_session",
            "datasets__sessions__annotations",
            "datasets__sessions__tiltseries_metadata",
            "datasets__sessions__tomogram_metadata",
        )
        serializer = SubmissionDepositionSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response({"submissions": serializer.data, "total_count": queryset.count()})


@extend_schema_view(
    create=extend_schema(
        summary="Create a dataset",
        description="Create a dataset under a deposition. Pass the deposition's `id` (from its "
        "create response) as `deposition` — not the `deposition_id`. `dataset_id` "
        "and `status` are set for you.",
        examples=[
            OpenApiExample(
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
            )
        ],
    ),
    partial_update=extend_schema(
        summary="Update a dataset (fields + nested funding / sessions)",
        description="Nested `funding` and `sessions` are FULL-REPLACE: any row omitted from the "
        "array is deleted. Each session entry must include `msi_session` (the MsiSession's id).",
        examples=[
            OpenApiExample(
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
            )
        ],
    ),
)
class DatasetViewSet(viewsets.ModelViewSet):
    """Submit-unit CRUD + per-dataset actions."""

    permission_classes = [IsAuthenticated, IsDepositionOwnerOrReadOnly]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DatasetSerializer
    queryset = (
        Dataset.objects.all()
        .select_related("deposition", "job")
        .prefetch_related("funding", "sessions", "sessions__annotations__method_links")
    )

    def get_queryset(self):
        qs = super().get_queryset()
        deposition_id = self.request.query_params.get("deposition")
        if deposition_id:
            qs = qs.filter(deposition_id=deposition_id)
        return qs

    def perform_create(self, serializer):
        deposition = serializer.validated_data["deposition"]
        if deposition.submitter_user_id != self.request.user.id:
            raise PermissionDenied("You can only add datasets to your own depositions.")
        dataset_id = None
        try:
            dataset_id = get_reservation_service().reserve_new_dataset()
        except Exception:
            logger.exception("Failed to reserve dataset id; saving without one")
        serializer.save(dataset_id=dataset_id)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        from .services.submit import submit_dataset_prep

        dataset = self.get_object()
        try:
            job = submit_dataset_prep(dataset)
        except SubmissionValidationError as error:
            return Response({"detail": error.public_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Dataset %s prep submit failed to reach the cluster", pk)
            return Response(
                {"detail": "Couldn't reach the cluster to submit. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {"state": job.state, "dataset_status": job.dataset_status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"])
    def push(self, request, pk=None):
        from .services.submit import submit_dataset_push

        dataset = self.get_object()
        try:
            job = submit_dataset_push(dataset)
        except SubmissionValidationError as error:
            return Response({"detail": error.public_message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Dataset %s push failed to reach the cluster", pk)
            return Response(
                {"detail": "Couldn't reach the cluster to push. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {"state": job.state, "dataset_status": job.dataset_status},
            status=status.HTTP_202_ACCEPTED,
        )

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
        "removed. Each annotation's `method_links` are written inline (upsert by id).",
        examples=[
            OpenApiExample(
                "Save metadata + annotations",
                request_only=True,
                value={
                    "tiltseries_metadata": {
                        "acceleration_voltage": 300,
                        "pixel_spacing": 1.5,
                        "tilt_min": -60,
                        "tilt_max": 60,
                        "tilt_step": 3,
                    },
                    "tomogram_metadata": [
                        {
                            "flavor": "denoised",
                            "voxel_spacing": 7.84,
                            "reconstruction_method": "WBP",
                            "ctf_corrected": True,
                            "processing": "denoised",
                            "processing_software": "DenoisET",
                            "is_visualization_default": True,
                        },
                        {
                            "flavor": "filtered",
                            "voxel_spacing": 7.84,
                            "reconstruction_method": "WBP",
                            "ctf_corrected": True,
                            "processing": "filtered",
                            "is_visualization_default": False,
                        },
                    ],
                    "annotations": [
                        {
                            "copick_kind": "picks",
                            "copick_ref": "ribosome-0",
                            "object_name": "ribosome",
                            "object_count": 1200,
                            "method_type": "automated",
                            "is_selected": True,
                            "method_links": [
                                {
                                    "link_type": "source_code",
                                    "link": "https://github.com/example/picking-model",
                                    "custom_name": "Picking model repo",
                                },
                            ],
                        },
                    ],
                },
            )
        ],
    ),
)
class DepositionSessionViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Session detail save. No create/list/delete — managed via dataset nested sessions."""

    permission_classes = [IsAuthenticated, IsDepositionOwnerOrReadOnly]
    http_method_names = HTTP_METHODS_NO_PUT
    serializer_class = DepositionSessionSerializer
    queryset = DepositionSession.objects.all().select_related("dataset__deposition")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.prefetch_related("annotations__method_links")
        return qs

    @action(detail=True, methods=["post"], url_path="auto-fill")
    def auto_fill(self, request, pk=None):
        """Run `cryoetportalprep init` on the cluster and populate this session's metadata."""
        session = self.get_object()
        if not session.aretomo_run_name:
            return Response(
                {"detail": "Select an AreTomo run for this session before auto-filling."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run_number = (
            session.aretomo_run_name if session.aretomo_run_name.startswith("run") else f"run{session.aretomo_run_name}"
        )

        msi_session = session.msi_session
        cluster_id = cluster_id_for_run(msi_session.name, run_number, default=DEPOSITION_DEFAULT_CLUSTER_ID)
        try:
            cluster = Cluster.objects.get(cluster_id=cluster_id, is_active=True)
        except Cluster.DoesNotExist:
            return Response(
                {"detail": f"Unknown cluster for this run: {cluster_id}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        aretomo3_dir = resolve_review_path(
            "proc_dir",
            cluster,
            msi_session=msi_session,
            proc_software="aretomo3",
            proc_run=run_number,
        )

        started = time.monotonic()
        result = run_autofill_init(cluster_id, aretomo3_dir, msi_session.name)
        if not result["filled"]:
            logger.warning(
                "auto-fill failed for session %s run %s on %s: %s",
                msi_session.name,
                run_number,
                cluster_id,
                result["reason"],
            )
            user_messages = {
                "ssh_disabled": "Auto-fill isn't available here.",
                "ssh_error": "Couldn't reach the cluster to auto-fill. Please try again.",
            }
            user_message = user_messages.get(
                result["reason"],
                "Check the AreTomo run on the Sources step.",
            )
            return Response({"detail": user_message}, status=status.HTTP_502_BAD_GATEWAY)

        raw = result["session"]
        mapped = map_session_to_metadata(raw)
        TiltseriesMetadata.objects.update_or_create(
            session=session,
            defaults={
                **mapped["tiltseries"],
                **map_session_plan_to_instrument_metadata(msi_session.session_plan),
                "autofill_metadata": raw,
            },
        )
        for tomo in mapped["tomograms"]:
            TomogramMetadata.objects.update_or_create(
                session=session,
                flavor=tomo["flavor"],
                defaults={**tomo, "autofill_metadata": raw},
            )
        kept_flavors = {tomo["flavor"] for tomo in mapped["tomograms"]}
        session.tomogram_metadata.exclude(flavor__in=kept_flavors).delete()

        session.last_autofill_at = timezone.now()
        session.last_autofill_duration_seconds = round(time.monotonic() - started)
        session.save(update_fields=["last_autofill_at", "last_autofill_duration_seconds", "updated_at"])
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"], url_path="subset-csv")
    def subset_csv(self, request, pk=None):
        """Parse uploaded subset into session.subset_selection. Cluster files are written at submit."""
        session = self.get_object()
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in (".json", ".csv"):
            return Response(
                {"detail": "Unsupported file type - upload a .json or .csv."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            raw = upload.read().decode("utf-8")
            selection = json.loads(raw) if ext == ".json" else list(csv.DictReader(io.StringIO(raw)))
        except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as exc:
            logger.warning("subset file parse failed: %s", exc)
            return Response(
                {"detail": "Could not parse the uploaded file - check its format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.subset_selection = selection
        session.subset_filename = upload.name
        session.subset_csv_path = ""
        session.save(update_fields=["subset_selection", "subset_filename", "subset_csv_path", "updated_at"])
        return Response({"subset_selection": selection, "subset_filename": upload.name})
