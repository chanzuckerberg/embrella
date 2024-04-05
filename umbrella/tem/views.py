from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import SessionForm, ReserveSessionForm, UpdateNotesForm
from . import models
from .models import Session, SessionPlan, Software
from projects.models import Project
from cryo_grids.models import CryoGrid
from tem.models import SessionPlan
from django.core.serializers import serialize
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json


def detail(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    if request.method == 'POST':
        new_notes = request.POST['notes']
        session.notes = new_notes
        session.save()
    field_objs = session._meta.get_fields()
    fields = {}
    for f in field_objs:
        fields[f.name] = getattr(session, f.name)
        # ManyToManyField
        if hasattr(fields[f.name], 'all'):
            fields[f.name] = list(map((lambda x: x.__str__()), fields[f.name].all()))
    form = UpdateNotesForm(instance=session)
    # context = {
    #     "data": session,
    #     "fields": fields,
    #     "paths": {
    #         'frame path pattern': session.get_session_frame_glob(),
    #         'sum image path pattern': session.get_session_sum_image_glob(),
    #         'parent path pattern': session.get_session_parent_glob(),
    #         'atlas image path pattern': session.get_session_atlas_glob(),
    #         "update_notes": form,
    #     }
    # }
    context = {
        "data": session,
        "fields": fields,
        "paths": {
            'frame path pattern': session.session_plan.frame_format,
            # 'sum image path pattern': session.session_software(),
            # 'parent path pattern': session.get_session_parent_glob(),
            # 'atlas image path pattern': session.get_session_atlas_glob(),
            "update_notes": form,
        }
    }
    return render(request, "tem/detail.html", context)


def reserve_session(request):
    if request.method == 'POST':
        form = ReserveSessionForm(request.POST)
        name = models.suggest_name('t')
        plan_id = int(request.POST['session_plan'])
        return render(request, reverse("tem:create"))
    else:
        form = ReserveSessionForm()
        return render(request, "tem/reserve.html", {"form": form})


# def create_session(request):
#     print(request.POST)
#     # plan_ids = list(map((lambda x: int(x)), request.POST['session_plan']))
#
#     session_plan_id = int(request.POST['session_plan'])
#
#     project_id = int(request.POST['project'])
#     grid_id = int(request.POST['grid'])
#     # TODO suggest name with prefix
#     name = models.suggest_name('')
#     if request.method == 'POST':
#         session_instance = Session.objects.create(
#             name=name,
#             user=request.user,
#             session_plan = SessionPlan.objects.get(pk=session_plan_id),
#             project=Project.objects.get(pk=project_id),
#             grid=CryoGrid.objects.get(pk=grid_id))
#         # manytomany add
#         # for plan_id in plan_ids:
#         #     print(plan_id)
#         #     session_instance.session_plan.add(plan_id)
#         session_instance.session_plan.add(plan_ids[0])
#         session_instance.save()
#         return HttpResponseRedirect(reverse('tem:detail', args=(session_instance.id,)))

def create_session(request):
    if request.method == 'POST':
        print(request.POST)

        # Since session_plan is expected to be a single value, we directly convert it to an integer
        session_plan_id = int(request.POST['session_plan'])

        # Extracting other necessary IDs from the POST request
        project_id = int(request.POST['project'])
        grid_id = int(request.POST['grid'])

        # Suggest a name for the session, you might need to implement models.suggest_name on your own
        name = models.suggest_name('')  # Assuming models.suggest_name is implemented elsewhere

        # Creating a new Session instance
        session_instance = Session.objects.create(
            name=name,
            user=request.user,
            session_plan=SessionPlan.objects.get(pk=session_plan_id),  # Assuming session_plan_id is valid
            project=Project.objects.get(pk=project_id),  # Assuming project_id is valid
            grid=CryoGrid.objects.get(pk=grid_id)  # Assuming grid_id is valid
        )

        # Since there's only one session_plan, we don't need a loop here to add session plans
        session_instance.save()
        # Redirecting to the detail view of the created session
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
    # Check if the 'valid' parameter is present and set to 'true'
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    # Retrieve the 'name' parameter from the GET call, if it exists
    name_param = request.GET.get('name')

    software_query = Software.objects.all()

    # Serialize the query set
    serialized_paths = serialize('json', software_query)

    if not name_param:
        entire_result = json.loads(serialized_paths)
        return JsonResponse(entire_result, safe=False)

    for item in json.loads(serialized_paths):
        name = item.get('fields').get('name')
        if name_param.lower() == name.lower():
            return JsonResponse(item, safe=False)

    return JsonResponse({'No result found': 'No matching software found'}, status=200)