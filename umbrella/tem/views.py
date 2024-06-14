from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import MsiSessionForm, ReserveMsiSessionForm, UpdateNotesForm
from .forms import ScreenSessionGroupForm, ReserveScreenSessionGroupForm, UpdateOrderForm
from . import models
from stores.models import Path
from .models import MsiSession, SessionPlan, Software
from projects.models import Project
from cryo_grids.models import CryoGrid, CryoGridCassette
from tem.models import SessionPlan, SoftwareFieldsResponse, SoftwareResponseModel, ErrorResponse, PathInfo, UserBase, ProjectBase, MsiSessionBase
from tem.models import ScreenSessionGroup, AtlasSession
from django.core.serializers import serialize
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json

def detail(request, session_id):
    session = get_object_or_404(MsiSession, pk=session_id)
    if request.method == 'POST':
        new_notes=request.POST['notes']
        new_atlas_session=request.POST['atlas_session']
        session.notes = new_notes
        if new_atlas_session:
            session.atlas_session = AtlasSession.objects.get(pk=new_atlas_session)
        else:
            session.atlas_session = None
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
        form = ReserveMsiSessionForm(request.POST)
        name = models.suggest_name('t')
        plan_id=int(request.POST['session_plan'])
        return render(request, reverse("tem:create"))
    else:
        form = ReserveMsiSessionForm()
        return render(request, "tem/reserve.html", {"form": form})

def create_session(request):
    plan_id=int(request.POST['session_plan'])
    project_id=int(request.POST['project'])
    grid_id=int(request.POST['grid'])
    # TODO suggest name with prefix
    name = models.suggest_name('')
    if request.method == 'POST':
        grid_instance = CryoGrid.objects.get(pk=grid_id)
        session_instance = MsiSession.objects.create(
                    name=name,
                    user=request.user,
                    project=Project.objects.get(pk=project_id),
                    grid=grid_instance,
                    session_plan=SessionPlan.objects.get(pk=plan_id),
        )
        session_instance.save()
        my_pk = session_instance.id
        # default to the latest screening grid atlas if available
        atlas_session = AtlasSession.objects.filter(grid=grid_instance).last()
        session_instance.atlas_session = atlas_session
        path_dicts = {}
        session_instance.frames = session_instance.get_session_path('frames')
        session_instance.sums = session_instance.get_session_path('sums')
        session_instance.mdocs = session_instance.get_session_path('mdocs')
        session_instance.parents = session_instance.get_session_path('parents')
        if atlas_session:
            session_instance.atlas = atlas_session.atlas
        session_instance.save()
        return HttpResponseRedirect(reverse('tem:detail', args=(session_instance.id,)))

#############
#Screening
############
def scrn_group_detail(request, scrn_group_id):
    '''
    Render the details of the screen session group
    '''
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

def reserve_scrn_session_group(request,error_msg=''):
    '''
    Render the form to create screen session group.
    '''
    form = ReserveScreenSessionGroupForm()
    return render(request, "tem/scrnreserve.html", {"form": form})

def _validate_order_list(cassette, order_list):
    valid = True
    for i in order_list:
        grids=CryoGrid.objects.filter(grid_cassette=cassette,slot_number_in_cassette=i)
        if len(grids) != 1:
            return False
    return valid
    
def create_scrn_session_group(request):
    '''
    Validate and create the screen session group and screen sessions
    '''
    plan_id = int(request.POST['session_plan'])
    cassette_id = int(request.POST['cassette'])
    cassette=CryoGridCassette.objects.get(pk=cassette_id)
    session_plan=SessionPlan.objects.get(pk=plan_id)
    order_str = request.POST['order']
    order_list = models.parse_integer_order_list(order_str)
    error_msg = ''
    if not _validate_order_list(cassette, order_list):
        # Don't save anything.
        # TODO: send error message to the page.
        return HttpResponseRedirect(reverse('tem:scrnreserve'))
    name = models.suggest_name('','ScreenSessionGroup')
    if request.method == 'POST':
        # save the validated group
        group_instance = ScreenSessionGroup.objects.create(
                    name=name,
                    cassette=cassette,
                    session_plan=session_plan,
                    order= order_str,
        )
        group_instance.save()
        for i in order_list:
            # create screen session for each grid and make association with
            # the group 
            grids=CryoGrid.objects.filter(grid_cassette=cassette,slot_number_in_cassette=i)
            _create_scrn_session(request.user, group_instance, grids[0])
    return HttpResponseRedirect(reverse('tem:scrndetail', args=(group_instance.id,)))

def _create_scrn_session(user,group_instance,grid):
    plan = group_instance.session_plan
    name = models.suggest_scrn_session_name('',group_instance)
    session_instance = AtlasSession.objects.create(
                    name=name,
                    grid=grid,
                    group=group_instance,
    )
    session_instance.save()
    my_pk = session_instance.id
    path_dicts = {}
    session_instance.atlas = session_instance.get_session_path('atlas')
    session_instance.save()
    return

@require_http_methods(["GET"])
def get_all_sessions(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    # Retrieve the 'name' parameter from the GET request, defaulting to None if not provided
    session_name = request.GET.get('name', None)

    # Fetch sessions and related stores_path records, filter by name if provided
    if session_name:
        sessions = MsiSession.objects.filter(name=session_name).select_related(
            'grid', 'project', 'user', 'mdocs', 'sums', 'parents', 'atlas', 'frames'
        )
    else:
        sessions = MsiSession.objects.select_related(
            'grid', 'project', 'user', 'mdocs', 'sums', 'parents', 'atlas', 'frames'
        ).all()

    session_list = []
    for session in sessions:
        # Create Pydantic model instances
        session_data = MsiSessionBase(
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
