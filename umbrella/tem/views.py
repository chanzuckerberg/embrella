from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import SessionForm, ReserveSessionForm, UpdateNotesForm
from . import models
from .models import Session, SessionPlan, Software
from projects.models import Project
from cryo_grids.models import CryoGrid
from tem.models import SessionPlan, SoftwareFieldsResponse, SoftwareResponseModel, ErrorResponse, PathInfo, UserBase, ProjectBase, SessionBase
from django.core.serializers import serialize
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
def detail(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    if request.method == 'POST':
        new_notes=request.POST['notes']
        session.notes = new_notes
        session.save()
    field_objs = session._meta.get_fields()
    fields = {}
    for f in field_objs:
        try:
            fields[f.name] = getattr(session, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
        #ManyToManyField
        if hasattr(fields[f.name],'all'):
            fields[f.name] = list(map((lambda x: x.__str__()),fields[f.name].all()))
    form = UpdateNotesForm(instance=session)
    context = {
            "data": session,
            "fields": fields,
            "paths": {
                    'frame path pattern':session.get_session_frames_glob(),
                    'sum image path pattern':session.get_session_sums_glob(),
                    'mdoc path pattern':session.get_session_mdocs_glob(),
                    'parent path pattern':session.get_session_parents_glob(),
                    'atlas image path pattern':session.get_session_atlas_glob(),
            "update_notes": form,
            }
    }
    return render(request, "tem/detail.html", context)

def reserve_session(request):
    if request.method == 'POST':
        form = ReserveSessionForm(request.POST)
        name = models.suggest_name('t')
        plan_id=int(request.POST['session_plan'])
        return render(request, reverse("tem:create"))
    else:
        form = ReserveSessionForm()
        return render(request, "tem/reserve.html", {"form": form})

def create_session(request):
    plan_id=int(request.POST['session_plan'])
    project_id=int(request.POST['project'])
    grid_id=int(request.POST['grid'])
    # TODO suggest name with prefix
    name = models.suggest_name('')
    if request.method == 'POST':
        session_instance = Session.objects.create(
                    name=name,
                    user=request.user,
                    project=Project.objects.get(pk=project_id),
                    grid=CryoGrid.objects.get(pk=grid_id),
                    session_plan=SessionPlan.objects.get(pk=plan_id),
        )
        session_instance.save()
        my_pk = session_instance.id
        path_dicts = {}
        session_instance.frames = session_instance.get_session_path('frames')
        session_instance.sums = session_instance.get_session_path('sums')
        session_instance.mdocs = session_instance.get_session_path('mdocs')
        session_instance.mdocs = session_instance.get_session_path('parents')
        session_instance.mdocs = session_instance.get_session_path('atlas')
        session_instance.save()
        return HttpResponseRedirect(reverse('tem:detail', args=(session_instance.id,)))


@require_http_methods(["GET"])
def get_all_sessions(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    # Retrieve the 'name' parameter from the GET request, defaulting to None if not provided
    session_name = request.GET.get('name', None)

    # Fetch sessions and related stores_path records, filter by name if provided
    if session_name:
        sessions = Session.objects.filter(name=session_name).select_related(
            'grid', 'project', 'user', 'mdocs', 'sums', 'parents', 'atlas', 'frames'
        )
    else:
        sessions = Session.objects.select_related(
            'grid', 'project', 'user', 'mdocs', 'sums', 'parents', 'atlas', 'frames'
        ).all()

    session_list = []
    for session in sessions:
        # Create Pydantic model instances
        session_data = SessionBase(
            id=session.id,
            name=session.name,
            notes=session.notes,
            user=UserBase(username=session.user.username),
            project=ProjectBase(name=session.project.name),
            frames=PathInfo(
                static_path=session.frames.static_path if session.frames.static_path else None,
                overlay_path=session.frames.overlay_path if session.frames.overlay_path else None
            ),
            mdocs=PathInfo(
                static_path=session.mdocs.static_path if session.mdocs.static_path else None,
                overlay_path=session.mdocs.overlay_path if session.mdocs.overlay_path else None
            ),
            sums=PathInfo(
                static_path=session.sums.static_path if session.sums.static_path else None,
                overlay_path=session.sums.overlay_path if session.sums.overlay_path else None
            ),
            parents=PathInfo(
                static_path=session.parents.static_path if session.parents.static_path else None,
                overlay_path=session.parents.overlay_path if session.parents.overlay_path else None
            ),
            atlas=PathInfo(
                static_path=session.atlas.static_path if session.atlas.static_path else None,
                overlay_path=session.atlas.overlay_path if session.atlas.overlay_path else None
            )
        )
        # Convert Pydantic model to dictionary and append to the list
        session_list.append(session_data.dict())

    # Use JsonResponse to send back a list of dictionaries
    return JsonResponse(session_list, safe=False)

@require_http_methods(["GET"])
def get_all_image_paths(request):
    # Check for a valid request
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    name_param = request.GET.get('name')

    # Query the Software table and prefetch related paths via nested "select_related"
    software_query = Software.objects.prefetch_related(
        'frames__static_path', 'sums__static_path', 'mdocs__static_path',
        'parents__static_path', 'atlas__static_path'
    ).all()

    result_list = []
    for software in software_query:
        # Constructing the response data with nested paths
        software_data = SoftwareResponseModel(
            model= "tem.software",
            pk= software.pk,
            fields= SoftwareFieldsResponse(
                name= software.name,
                frames= PathInfo(
                    static_path= software.frames.static_path.static_path if software.frames and software.frames.static_path else None,
                    overlay_path= software.frames.overlay_path if software.frames else None,
                ),
                sums= PathInfo(
                    static_path= software.sums.static_path.static_path if software.sums and software.sums.static_path else None,
                    overlay_path= software.sums.overlay_path if software.sums else None,
                ),
                mdocs= PathInfo(
                    static_path= software.mdocs.static_path.static_path if software.mdocs and software.mdocs.static_path else None,
                    overlay_path= software.mdocs.overlay_path if software.mdocs else None,
                ),
                parents= PathInfo(
                    static_path= software.parents.static_path.static_path if software.parents and software.parents.static_path else None,
                    overlay_path= software.parents.overlay_path if software.parents else None,
                ),
                atlas= PathInfo(
                    static_path= software.atlas.static_path.static_path if software.atlas and software.atlas.static_path else None,
                    overlay_path= software.atlas.overlay_path if software.atlas else None,
                ),
            )
        )
        result_list.append(software_data.dict())

    if not name_param:
        return JsonResponse(result_list, safe=False)

    # Filter results based on the name parameter
    filtered_results = [item for item in result_list if item['fields']['name'].lower() == name_param.lower()]
    if filtered_results:
        return JsonResponse(filtered_results[0], safe=False)

    # Return error if no matching software is found
    return JsonResponse({'error': 'No matching software found'}, status=404, safe=False)
