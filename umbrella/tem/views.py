import re

from cryo_grids.models import CryoGridCassette
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from projects.models import Project
from rest_framework.decorators import api_view
from stores.models import Path

from tem.models import (
    AtlasSession,
    ScreenSessionGroup,
)

from . import models
from .forms import (
    ReserveScreenSessionGroupForm,
    UpdateNotesForm,
)
from .models import CryoGrid, Magnification, MsiSession, SessionPlan


def detail(request, session_id):
    session = get_object_or_404(MsiSession, pk=session_id)
    if request.method == "POST":
        new_notes = request.POST["notes"]
        new_atlas_session = request.POST["atlas_session"]
        new_project = request.POST.get("project")
        session.notes = new_notes
        if new_atlas_session:
            session.atlas_session = AtlasSession.objects.get(pk=new_atlas_session)
        else:
            session.atlas_session = None
        if new_project:
            session.project = Project.objects.get(pk=new_project)
        session.save()
    field_objs = session._meta.get_fields()
    fields = {}
    for f in field_objs:
        if f.related_model == Path:
            continue
        try:
            fields[f.name] = getattr(session, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
        # ManyToManyField
        if hasattr(fields[f.name], "all"):
            fields[f.name] = list(map((lambda x: x.__str__()), fields[f.name].all()))
    form = UpdateNotesForm(instance=session)
    print(fields)
    context = {
        "data": session,
        "fields": fields,
        "paths": {
            # Directories, not patterns, since the split: the filenames live on the
            # resolved FilePattern instead.
            "frame directory": session.get_session_dir("frames"),
            "sum image directory": session.get_session_dir("sums"),
            "mdoc directory": session.get_session_dir("mdocs"),
            "parent image directory": session.get_session_dir("parents"),
            "atlas image directory": session.get_session_dir("atlas"),
            "update_notes": form,
        },
    }
    return render(request, "tem/detail.html", context)


def reserve_session(request):
    # Form is now a single-page JS app that calls v1 APIs directly.
    # No server-side form logic needed — just render the template.
    return render(request, "tem/reserve.html")


def create_msi_name(request, data={}):
    """
    Set template display of the session_plan and grid selection.
    Suggest name of the session but allow user to change.
    """
    if request.method == "POST":
        plan_id = int(request.POST["session_plan"])
        project_id = int(request.POST["project"])
        grid_id = int(request.POST["grid"])
        magnification_id = request.POST.get("magnification")
        project = Project.objects.get(pk=project_id)
        session_plan = SessionPlan.objects.get(pk=plan_id)
        grid = CryoGrid.objects.get(pk=grid_id)
        magnification = Magnification.objects.get(pk=magnification_id) if magnification_id else None
        name = models.suggest_name("")
        context = {
            "default_name": name,
            "session_plan": session_plan,
            "project": project,
            "grid": grid,
            "magnification": magnification,
        }
        if "error_msg" in data.keys():
            context["error_msg"] = data["error_msg"]
    return render(request, "tem/create_msi_name.html", context)


def validate_msi_name(request):
    """
    Make sure the name does not exists before creating the session.
    """
    if "name" in request.POST.keys():
        name_by_user = request.POST["name"]
        regex = re.compile(r"[@_!#$%^&*()<>?/\|}{~:]")
        if regex.search(name_by_user) or len(name_by_user.split(" ")) > 1:
            data = {
                "error_msg": 'Session name "%s" can not include special characters nor space.  Try again, please.'
                % name_by_user
            }
            return create_msi_name(request, data)
        sessions_with_name = MsiSession.objects.filter(name=name_by_user)
        if sessions_with_name.count() == 0:
            return create_session(request)
        data = {"error_msg": "Session name %s exists in Embrella. Try another one, please." % name_by_user}
    else:
        data = {"error_msg": "No session name chosen. Try again, please."}

    return create_msi_name(request, data)


def create_session(request):
    """
    Create session from posted values
    """
    # Get values from POST with error handling
    try:
        plan_id = int(request.POST.get("session_plan"))
        project_id = int(request.POST.get("project"))
        grid_id = int(request.POST.get("grid"))
        user_id = int(request.user.id)
        name = request.POST.get("name")

        if not all([plan_id, project_id, grid_id, name]):
            raise ValueError("Missing required fields")

    except (TypeError, ValueError, IndexError):
        # Return to form with error message
        data = {"error_msg": "Invalid form data. Please ensure all fields are filled correctly."}
        return create_msi_name(request, data)

    if request.method == "POST":
        grid_instance = CryoGrid.objects.get(pk=grid_id)
        magnification_id = request.POST.get("magnification")
        magnification = Magnification.objects.get(pk=magnification_id) if magnification_id else None
        session_instance = MsiSession.objects.create(
            name=name,
            project=Project.objects.get(pk=project_id),
            grid=grid_instance,
            session_plan=SessionPlan.objects.get(pk=plan_id),
            magnification=magnification,
            user=request.user,
        )
        session_instance.save()
        # default to the latest screening grid atlas if available
        session_instance.atlas_session = AtlasSession.objects.filter(grid=grid_instance).last()
        session_instance.resolve_role_paths()
        session_instance.save()
        return HttpResponseRedirect(reverse("tem:detail", args=(session_instance.id,)))


#############
# Screening
############
def scrn_group_detail(request, scrn_group_id):
    """
    Render the details of the screen session group
    """
    session_group = get_object_or_404(ScreenSessionGroup, pk=scrn_group_id)
    field_objs = session_group._meta.get_fields()
    fields = {}
    for f in field_objs:
        try:
            fields[f.name] = getattr(session_group, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
    order_list = models.parse_integer_order_list(session_group.order)
    scrn_sessions = []
    scrn_sessions = AtlasSession.objects.filter(
        group=session_group,
    ).order_by("order_in_screen")
    context = {
        "data": session_group,
        "fields": fields,
        "screens": scrn_sessions,
    }
    return render(request, "tem/scrndetail.html", context)


def reserve_scrn_session_group(request, error_msg=""):
    """
    Render the form to create screen session group.
    """
    form = ReserveScreenSessionGroupForm()
    return render(request, "tem/scrnreserve.html", {"form": form})


def _validate_order_list(cassette, order_list):
    valid = True
    for i in order_list:
        grids = CryoGrid.objects.filter(grid_cassette=cassette, slot_number_in_cassette=i)
        if len(grids) != 1:
            return False
    return valid


def create_scrn_session_group(request):
    """
    Validate and create the screen session group and screen sessions
    """
    plan_id = int(request.POST["session_plan"])
    print(plan_id)
    cassette_id = int(request.POST["cassette"])
    cassette = CryoGridCassette.objects.get(pk=cassette_id)
    session_plan = SessionPlan.objects.get(pk=plan_id)
    # print(session_plan)
    order_str = request.POST["order"]
    order_list = models.parse_integer_order_list(order_str)
    error_msg = ""
    if not _validate_order_list(cassette, order_list):
        # Don't save anything.
        # TODO: send error message to the page.
        return HttpResponseRedirect(reverse("tem:scrnreserve"))
    name = models.suggest_name("", "ScreenSessionGroup")
    if request.method == "POST":
        # save the validated group
        group_instance = ScreenSessionGroup.objects.create(
            name=name,
            cassette=cassette,
            session_plan=session_plan,
            order=order_str,
        )
        group_instance.save()
        for i in order_list:
            # create screen session for each grid and make association with
            # the group
            grids = CryoGrid.objects.filter(grid_cassette=cassette, slot_number_in_cassette=i)
            _create_scrn_session(request.user, group_instance, grids[0])
    return HttpResponseRedirect(reverse("tem:scrndetail", args=(group_instance.id,)))


def _create_scrn_session(user, group_instance, grid):
    plan = group_instance.session_plan
    name = models.suggest_scrn_session_name("", group_instance)
    session_instance = AtlasSession.objects.create(
        name=name,
        grid=grid,
        group=group_instance,
    )
    session_instance.save()
    my_pk = session_instance.id
    path_dicts = {}
    session_instance.atlas = session_instance.resolve_path_row("atlas")
    session_instance.save()
    return


@extend_schema(
    methods=["GET"],
    description="Returns all unique screen session group names.",
    parameters=[
        OpenApiParameter(name="valid", required=True, type=OpenApiTypes.BOOL, description="Must be 'true'"),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_all_scrns(request):
    if request.GET.get("valid", "true") != "true":
        return JsonResponse({"error": "Invalid request"}, status=400)
    try:
        unique_names = ScreenSessionGroup.objects.values_list("name", flat=True).distinct()
        return JsonResponse({"unique_names": list(unique_names)}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def render_screening_form(request):
    data_id = request.GET.get("id")  # Example way to get data.id, adjust as needed.

    context = {
        "title": "Screening Session",
        "data": {
            "id": data_id,
        },
    }
    return render(request, "tem/filter.html", context)


@extend_schema(
    methods=["GET"],
    description="Returns screening session group and associated atlas sessions by `session_name`.",
    parameters=[
        OpenApiParameter(
            name="session_name",
            required=True,
            type=OpenApiTypes.STR,
            description="Name of the screen session group to fetch",
        ),
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT,
    },
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_specific_session(request):
    session_name = request.GET.get("session_name")

    if not session_name:
        return JsonResponse({"error": "Session name not provided"}, status=400)

    try:
        scrn_session = get_object_or_404(ScreenSessionGroup, name=session_name)

        # Gather required information from the related models
        atlas_sessions = AtlasSession.objects.filter(group=scrn_session)
        session_data = []

        for atlas_session in atlas_sessions:
            session_plan = scrn_session.session_plan
            session_info = {
                "id": scrn_session.id,
                "name": scrn_session.name,
                "screening": atlas_session.name,
                "cassette": scrn_session.cassette.name if scrn_session.cassette else None,
                "session_plan": session_plan.software.name if session_plan and session_plan.software else None,
                "session_plan_id": session_plan.id if session_plan else None,
                "order_in_screen": atlas_session.order_in_screen,
                "atlas_id": atlas_session.id,
                "atlas_name": atlas_session.name,
                "grid_name": atlas_session.grid.name if atlas_session.grid else None,
                "grid_id": atlas_session.grid.id if atlas_session.grid else None,
                "quality": atlas_session.quality,
            }
            session_data.append(session_info)

        return JsonResponse({"sessions": session_data}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
