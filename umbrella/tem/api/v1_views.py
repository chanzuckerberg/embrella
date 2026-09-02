from drf_spectacular.utils import OpenApiParameter, extend_schema
from projects.models import Project
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from tem.models import (
    AtlasSession,
    CryoGrid,
    Magnification,
    MsiSession,
    SessionPlan,
    suggest_name,
)

from .serializers import (
    CreatedSessionSerializer,
    FormOptionsSerializer,
    MagnificationSerializer,
    MsiSessionCreateSerializer,
    SuggestNameSerializer,
)


@extend_schema(
    methods=["POST"],
    tags=["TEM Sessions"],
    request=MsiSessionCreateSerializer,
    responses={201: CreatedSessionSerializer},
    description="Create a new TEM MSI session with auto-generated paths.",
)
@api_view(["POST"])
def create_session(request):
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
    session.resolve_role_paths()
    session.save()

    payload = {
        "id": session.id,
        "name": session.name,
        "project_name": project.name,
        "grid_name": str(grid),
        "session_plan_name": str(session_plan),
        "magnification_display": str(magnification) if magnification else None,
        "legacy_url": f"/legacy/tem/{session.id}/",
    }
    for role, path in session.role_paths.items():
        payload[role] = _role_halves(path, session.get_file_pattern(role))

    return Response(CreatedSessionSerializer(payload).data, status=status.HTTP_201_CREATED)


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
    ).select_related("scope", "camera", "imaging_workflow", "software")

    projects = Project.objects.all().order_by("name")

    return Response(
        {
            "session_plans": [{"id": sp.id, "name": str(sp)} for sp in session_plans],
            "projects": [{"id": p.id, "name": p.name} for p in projects],
        }
    )


@extend_schema(
    methods=["GET"],
    tags=["TEM Sessions"],
    responses={200: SuggestNameSerializer},
    description="Get an auto-generated session name based on the current date.",
)
@api_view(["GET"])
def suggest_session_name(request):
    name = suggest_name("")
    return Response({"suggested_name": name})


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
