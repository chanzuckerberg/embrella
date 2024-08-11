from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import ProcRunForm, ReserveTomoProcRunForm, UpdateNotesForm
from django.forms import CharField, HiddenInput, ModelChoiceField
from . import models
from processes.models import ProcRun, ProcPlan, ProcSoftware, RunPipeData, Tomograms
from processes.models import Annotation
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
    return render(request, "processes/ptdetail.html", context)

def reserve_run(request):
    print('Reserving')
    if request.method == 'POST':
        print('Post-----')
        form = ReserveTomoProcRunForm(request.POST)
        print(request.POST)
        if ('input_tomo' not in request.POST.keys() or not request.POST['input_tomo']) and 'msi_session' in request.POST.keys():
            session_id=int(request.POST['msi_session'])
            msi_session=MsiSession.objects.get(pk=session_id)
            input_tomo = ModelChoiceField(queryset=Tomograms.objects.filter(msi_session=msi_session))
            return render(request, "processes/ptselect.html", {"form": form, "input_tomo_field": input_tomo})
        else:
            print('reserve success', request.POST)
            return render(request, reverse("processes:ptselect"))
    else:
        form = ReserveTomoProcRunForm()
        input_tomo = ModelChoiceField(queryset=Tomograms.objects.all())
        return render(request, "processes/ptreserve.html", {"form": form, "input_tomo_field": input_tomo })

def create_run(request):
    if request.method == 'POST':
        plan_id=int(request.POST['proc_plan'])
        session_id=int(request.POST['msi_session'])
        input_tomo_id=int(request.POST['input_tomo'])
        input_tomo=Tomograms.objects.get(pk=input_tomo_id)
        input_objects = {'tomo':input_tomo}
        if 'input_pick' in request.POST.keys():
            input_pick_id=int(request.POST['input_pick'])
            input_pick=Annotation.objects.get(pk=input_pick_id)
            input_objects['pick']=input_pick
        else:
            input_pick_id = False
            input_objects['pick']=False
        msi_session=MsiSession.objects.get(pk=session_id)
        proc_plan=ProcPlan.objects.get(pk=plan_id)
        name = models.suggest_name('run',msi_session,proc_plan)
        run_instance = ProcRun.objects.create(
                    name=name,
                    msi_session=msi_session,
                    proc_plan=proc_plan,
        )
        run_instance.save()
        run_instance.save_pipe_run_data()
        run_instance.create_tomogram_collection(input_objects)
        return HttpResponseRedirect(reverse('processes:ptdetail', args=(run_instance.id,)))
