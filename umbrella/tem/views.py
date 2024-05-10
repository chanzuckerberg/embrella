from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import SessionForm, ReserveSessionForm, UpdateNotesForm
from . import models
from .models import Session, SessionPlan, Software
from projects.models import Project
from cryo_grids.models import CryoGrid
from tem.models import SessionPlan, SoftwareFieldsResponse, SoftwareResponseModel, ErrorResponse, PathInfo
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
        fields[f.name] = getattr(session, f.name)
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
                    #'parent path pattern':session.get_session_parent_glob(),
                    #'atlas image path pattern':session.get_session_atlas_glob(),
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
        session_instance.save()
        return HttpResponseRedirect(reverse('tem:detail', args=(session_instance.id,)))

@require_http_methods(["GET"])
def get_all_sessions(request):
    if not request.GET.get('valid', 'true') == 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    session_list = Session.objects.all()
    serialized_sessions = serialize('json', session_list)
    session_data = json.loads(serialized_sessions)
    return JsonResponse(session_data, safe=False)

@require_http_methods(["GET"])
def get_all_image_paths(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    name_param = request.GET.get('name')

    software_query = Software.objects.select_related(
        'frames', 'sums', 'mdocs', 'parents', 'atlas'
    ).all()

    result_list: List[dict] = []
    for software in software_query:
        software_data = SoftwareResponseModel(
            model="tem.software",
            pk=software.pk,
            fields=SoftwareFieldsResponse(
                name=software.name,
                frames=PathInfo(
                    static_path=software.frames.static_path if software.frames else None,
                    overlay_path=software.frames.overlay_path if software.frames else None,
                ),
                sums=PathInfo(
                    static_path=software.sums.static_path if software.sums else None,
                    overlay_path=software.sums.overlay_path if software.sums else None,
                ),
                mdocs=PathInfo(
                    static_path=software.mdocs.static_path if software.mdocs else None,
                    overlay_path=software.mdocs.overlay_path if software.mdocs else None,
                ),
                parents=PathInfo(
                    static_path=software.parents.static_path if software.parents else None,
                    overlay_path=software.parents.overlay_path if software.parents else None,
                ),
                atlas=PathInfo(
                    static_path=software.atlas.static_path if software.atlas else None,
                    overlay_path=software.atlas.overlay_path if software.atlas else None,
                )
            )
        )
        result_list.append(software_data.dict())

    if not name_param:
        return JsonResponse(content=result_list.dict())
    #case sensitive
    filtered_results = [item for item in result_list if item['fields']['name'].lower() == name_param.lower()]
    if filtered_results:
        return JsonResponse(data=filtered_results[0], safe=False)

    # Use ErrorResponse model correctly by converting it to a dictionary
    error_response = ErrorResponse(error='No matching software found')

    return JsonResponse(data=error_response.dict(), status=404, safe=False)