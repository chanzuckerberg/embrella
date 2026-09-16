from drf_spectacular.utils import OpenApiParameter, extend_schema
from projects.models import Project
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from common.sorting import msi_session_sort_key
from tem.models import (
    ACQUISITION_FIELDS,
    AcquisitionSettings,
    AtlasSession,
    CryoGrid,
    Magnification,
    MsiSession,
    SessionPlan,
    suggest_name,
)

from .serializers import (
    FormOptionsSerializer,
    MagnificationSerializer,
    MsiSessionCreateSerializer,
    SessionDetailSerializer,
    SessionListSerializer,
    SuggestNameSerializer,
)


@extend_schema(
    methods=["GET"],
    tags=["TEM Sessions"],
    responses={200: SessionListSerializer},
    description="All MSI sessions with their plan, newest first, for session pickers.",
)
@extend_schema(
    methods=["POST"],
    tags=["TEM Sessions"],
    request=MsiSessionCreateSerializer,
    responses={201: SessionDetailSerializer},
    description="Create a new TEM MSI session with auto-generated paths.",
)
@api_view(["GET", "POST"])
def sessions(request):
    if request.method == "GET":
        return _list_sessions()
    return _create_session(request)


def _list_sessions():
    plans = MsiSession.objects.select_related(
        "session_plan__scope",
        "session_plan__software",
        "session_plan__camera",
        "session_plan__imaging_workflow",
    )
    items = [
        {
            "name": session.name,
            "scope": session.session_plan.scope.name,
            "software": str(session.session_plan.software),
            "camera": session.session_plan.camera.name,
            "workflow": str(session.session_plan.imaging_workflow),
        }
        for session in plans
    ]
    items.sort(key=lambda item: msi_session_sort_key(item["name"]))
    return Response(SessionListSerializer({"sessions": items}).data)


def _create_session(request):
    serializer = MsiSessionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    session_plan = SessionPlan.objects.get(pk=data["session_plan_id"])
    project = Project.objects.get(pk=data["project_id"])
    grid = CryoGrid.objects.get(pk=data["grid_id"])
    magnification = None
    if data.get("magnification_id"):
        magnification = Magnification.objects.get(pk=data["magnification_id"])

    session = MsiSession.objects.create(
        name=data["name"],
        project=project,
        grid=grid,
        session_plan=session_plan,
        magnification=magnification,
        user=request.user,
    )

    # Auto-create Path objects based on software config
    # default to the latest screening grid atlas if available
    session.atlas_session = AtlasSession.objects.filter(grid=grid).last()
    session.acquisition = _snapshot_acquisition(session_plan, data)
    session.resolve_role_paths()
    session.save()

    return Response(SessionDetailSerializer(_session_payload(session)).data, status=status.HTTP_201_CREATED)


def _snapshot_acquisition(session_plan, data):
    """The session's own acquisition row: the plan's profile, with whatever the form posted on top."""
    overrides = {field: data[field] for field in ACQUISITION_FIELDS if field in data}
    label = AcquisitionSettings.snapshot_label(data["name"])
    profile = session_plan.acquisition_defaults
    if profile:
        return profile.snapshot(label, **overrides)
    return AcquisitionSettings.objects.create(label=label, **overrides)


@extend_schema(
    methods=["GET"],
    tags=["TEM Sessions"],
    responses={200: SessionDetailSerializer},
    description="One MSI session: plan, project, grid, and where each data role lands.",
)
@api_view(["GET"])
def session_detail(request, name):
    session = (
        MsiSession.objects.filter(name=name)
        .select_related("project", "grid", "session_plan", "magnification", "acquisition")
        .first()
    )
    if session is None:
        return Response({"detail": "Session '%s' not found." % name}, status=status.HTTP_404_NOT_FOUND)
    return Response(SessionDetailSerializer(_session_payload(session)).data)


def _session_payload(session):
    """What the created-session dialog and the launch form's session accordion both show."""
    payload = {
        "id": session.id,
        "name": session.name,
        "project_name": session.project.name if session.project else None,
        "grid_name": str(session.grid) if session.grid else None,
        "session_plan_name": str(session.session_plan),
        "magnification_display": str(session.magnification) if session.magnification else None,
        "acquisition": session.acquisition.values() if session.acquisition else None,
        "legacy_url": f"/legacy/tem/{session.id}/",
    }
    for role, path in session.role_paths.items():
        payload[role] = _role_halves(path, session.get_file_pattern(role))
    return payload


def _role_halves(path, pattern):
    """The directory and the filename glob for one role."""
    if not path:
        return {"directory": None, "pattern": None}
    return {"directory": str(path), "pattern": pattern.list_glob if pattern else None}


@extend_schema(
    methods=["GET"],
    tags=["TEM Sessions"],
    responses={200: FormOptionsSerializer},
    description="Get dropdown options for the session creation form (session plans and projects).",
)
@api_view(["GET"])
def form_options(request):
    session_plans = SessionPlan.objects.filter(
        imaging_workflow__workflow__in=["tomo", "sngl"],
    ).select_related("scope", "camera", "imaging_workflow", "software", "acquisition_defaults")

    projects = Project.objects.all().order_by("name")

    return Response(
        {
            "session_plans": [
                {
                    "id": sp.id,
                    "name": str(sp),
                    "workflow": str(sp.imaging_workflow),
                    "scope": sp.scope.name,
                    "software": str(sp.software),
                    "camera": sp.camera.name,
                    "acquisition_defaults": sp.acquisition_values(),
                }
                for sp in session_plans
            ],
            "projects": [{"id": p.id, "name": p.name} for p in projects],
        }
    )


def _plan_name_prefix(session_plan_id):
    """The plan's configured prefix; "" when the id is missing, malformed or unknown."""
    if not session_plan_id or not str(session_plan_id).isdigit():
        return ""
    plan = SessionPlan.objects.filter(pk=session_plan_id).only("name_prefix").first()
    return plan.name_prefix if plan else ""


@extend_schema(
    methods=["GET"],
    tags=["TEM Sessions"],
    parameters=[
        OpenApiParameter(
            name="session_plan_id",
            required=False,
            type=int,
            description="SessionPlan whose name_prefix to apply. Omitted or unknown: no prefix.",
        ),
    ],
    responses={200: SuggestNameSerializer},
    description="Auto-generated session name: <plan prefix><yymmmdd><letter>, e.g. s26jun08a.",
)
@api_view(["GET"])
def suggest_session_name(request):
    prefix = _plan_name_prefix(request.query_params.get("session_plan_id"))
    return Response({"suggested_name": suggest_name(prefix)})


@extend_schema(
    methods=["GET"],
    tags=["TEM Sessions"],
    parameters=[
        OpenApiParameter(
            name="session_plan_id",
            required=True,
            type=int,
            description="SessionPlan ID to filter magnifications by scope",
        ),
    ],
    responses={200: MagnificationSerializer(many=True)},
    description="Get magnifications filtered by a session plan's microscope scope.",
)
@api_view(["GET"])
def get_magnifications(request):
    session_plan_id = request.query_params.get("session_plan_id")
    if not session_plan_id:
        return Response([])
    try:
        plan = SessionPlan.objects.get(pk=session_plan_id)
    except SessionPlan.DoesNotExist:
        return Response([])
    mags = (
        Magnification.objects.filter(scope=plan.scope)
        .order_by("nominal_mag")
        .values("id", "nominal_mag", "mode", "index", "scope__name")
    )
    serializer = MagnificationSerializer(mags, many=True)
    return Response(serializer.data)
