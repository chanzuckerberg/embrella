from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ProcRunForm, ReserveFrameProcRunForm, UpdateNotesForm
from django.contrib.auth.decorators import login_required
from . import models
from processes.models import ProcRun, PipelinePlan, ProcSoftware, RunPipeData
from tem.models import MsiSession
from django.core.serializers import serialize
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json

def detail(request, run_id):
    run = get_object_or_404(ProcRun, pk=run_id)
    if request.method == 'POST':
        new_notes=request.POST['notes']
        run.notes = new_notes
        run.save()
    field_objs = run._meta.get_fields()
    fields = {}
    for f in field_objs:
        try:
            fields[f.name] = getattr(run, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
        except TypeError:
            print(f)
            continue
        #ManyToManyField
        if hasattr(fields[f.name],'all'):
            fields[f.name] = list(map((lambda x: x.__str__()),fields[f.name].all()))
    all_pipe_data = RunPipeData.objects.filter(run=run)
    form = UpdateNotesForm(instance=run)
    context = {
            "data": run,
            "fields": fields,
            "pipe_data": all_pipe_data,
            "paths": {
                    "update_notes": form,
            }
    }
    return render(request, "processes/detail.html", context)
@login_required
def reserve_run(request):
    if request.method == 'POST':
        form = ReserveFrameProcRunForm(request.POST)
        return render(request, reverse("processes:create"))
    else:
        form = ReserveFrameProcRunForm()
        return render(request, "processes/reserve.html", {"form": form})
@login_required
def create_run(request):
    plan_id=int(request.POST['proc_plan'])
    session_id=int(request.POST['msi_session'])
    msi_session=MsiSession.objects.get(pk=session_id)
    proc_plan=PipelinePlan.objects.get(pk=plan_id)
    name = models.suggest_name('run',msi_session,proc_plan)
    if request.method == 'POST':
        run_instance = ProcRun.objects.create(
                    name=name,
                    msi_session=msi_session,
                    proc_plan=proc_plan,
        )
        run_instance.save()
        my_pk = run_instance.id
        path_dicts = {}
        run_instance.save()
        run_instance.save_pipe_run_data()
        run_instance.create_tomogram_collection()
        return HttpResponseRedirect(reverse('processes:detail', args=(run_instance.id,)))

@require_http_methods(["GET"])
def get_all_runs(request):
    if not request.GET.get('valid', 'true') == 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    run_list = Session.objects.all()
    serialized_runs = serialize('json', run_list)
    run_data = json.loads(serialized_runs)
    return JsonResponse(run_data, safe=False)

@require_http_methods(["GET"])
def get_all_image_paths(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    name_param = request.GET.get('name')

    software_query = ProcSoftware.objects.select_related(
        'frames', 'sums', 'mdocs', 'parents', 'atlas'
    ).all()

    result_list: List[dict] = []
    for software in software_query:
        software_data = ProcSoftwareResponseModel(
            model="tem.software",
            pk=software.pk,
            fields=ProcSoftwareFieldsResponse(
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
