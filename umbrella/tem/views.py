from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import SessionForm, ReserveSessionForm, UpdateNotesForm
from . import models
from .models import Session, SessionPlan
from projects.models import Project
from cryo_grids.models import CryoGrid

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
                    'frame path pattern':session.get_session_frame_glob(),
                    'sum image path pattern':session.get_session_sum_image_glob(),
                    'parent path pattern':session.get_session_parent_glob(),
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
    plan_ids=list(map((lambda x:int(x)),request.POST['session_plan']))
    project_id=int(request.POST['project'])
    grid_id=int(request.POST['grid'])
    # TODO suggest name with prefix
    name = models.suggest_name('')
    if request.method == 'POST':
        session_instance = Session.objects.create(
                    name=name,
                    user=request.user,
                    project=Project.objects.get(pk=project_id),
                    grid=CryoGrid.objects.get(pk=grid_id))
        # manytomany add
        for plan_id in plan_ids:
            session_instance.session_plan.add(plan_id)
        session_instance.save()
        return HttpResponseRedirect(reverse('tem:detail', args=(session_instance.id,)))

