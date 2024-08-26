from django.contrib.auth.models import User
import sys
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
from tem.models import *
from stores.models import StaticPath,PathType, fill_place_holders
from processes.models import ProcSoftware,Task, PipelinePlan, Pipe, PipeInPlan, ReconMethod, TomogramVoxelSpacing
from processes.models import AnnotationMethod

def _get_first_of(model_class):
    return model_class.objects.get(pk=1)

def create_static_path(data_type):
    for data_type in ['pick','seg','galr']:
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{msi_session}/{run}/%s/{proc_software}/{proc_run}/{pipe}/' % data_type,
        )
    return instance

def get_static_path(data_type):
    qset = StaticPath.objects.filter(data_type=data_type)
    if qset:
        return qset[0]
    else:
        create_static_path(data_type)
        qset = StaticPath.objects.filter(data_type=data_type)
        return qset[0]

def createStandardTasks():
    task_names = ['pick particles',
                    'make particle 2d gallery',
                    'segmentate volume',
    ] ## or: 'compute CC score map', 'extract particles', 'make mini slabs', 'segment membranes'
    current_tasks = Task.objects.all()
    task_count = len(current_tasks)
    tasks = []
    for i, n in enumerate(task_names):
        tasks.append(Task.objects.create(name=n, step=i+task_count+1))
    return tasks

def create_pipeline_plan():
    tasks = createStandardTasks()
    pytom = ProcSoftware.objects.create(name='pytom',
                version='2024-03-10')
    gallery = ProcSoftware.objects.create(name='gallerymaker',
                version='2024-03-10')
    membr = ProcSoftware.objects.create(name='membrainseg',
                version='2024-03-10')
    for t in tasks[0:1]:
        pytom.capable_tasks.add(t)
    for t in tasks[1:2]:
        gallery.capable_tasks.add(t)
    for t in tasks[2:3]:
        membr.capable_tasks.add(t)
    plan = PipelinePlan.objects.create(name='pytom-pick')
    # AreTomo3-5A recon
    pipe1 = Pipe.objects.create(name='80s-ribosome',software=pytom)
    pipe2 = Pipe.objects.create(name='gallery',software=gallery) #or  name=gallery, software=slabpick,
    pipe3 = Pipe.objects.create(name='membrane',software=membr) #a pipe and a datatype??
    # AreTomo3-5A recon
    plan_pipe1 = PipeInPlan.objects.create(name='pick1',plan=plan,step=1,pipe=pipe1)
    # AreTomo3-10A recon
    plan_pipe2 = PipeInPlan.objects.create(name='pick2',plan=plan,step=2,pipe=pipe2)
    #input
    input_path_types = []
    #PathType may not be good enough to tell different software
    # TODO: make input only specify static_path, not PathType with software definition
    #output
    output_path_types = []
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('pick'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/output.txt',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('galr'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/output.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('seg'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/output.mrc',
    ))
    for t in tasks[0:1]:
        # everything at 5 Å except denoising
        pipe1.tasks_performed.add(t)
    for t in tasks[1:2]:
        # 10Å no CTF WBP
        pipe2.tasks_performed.add(t)
    for t in tasks[2:3]:
        # 10Å no CTF WBP
        pipe3.tasks_performed.add(t)
    # input/output
    pipe1.input.add(get_static_path('rec'))
    for p in output_path_types[0:1]:
        pipe1.output.add(p) 
    pipe2.input.add(get_static_path('pick'))
    for p in output_path_types[1:2]: #recon
       pipe2.output.add(p)
    pipe3.input.add(get_static_path('rec'))
    for p in output_path_types[2:3]:
       pipe3.output.add(p)
    # where the input are from
    input_rec = Pipe.objects.filter(name='vol002')[0]
    pipe1.input_pipe = input_rec
    pipe2.input_pipe = pipe1
    pipe3.input_pipe = input_rec
    # save
    pipe1.save()
    pipe2.save()
    pipe3.save()

def create_default_anno_methods():
    AnnotationMethod.objects.create(name='template matching')

def run():
    try:
        r = get_static_path('rec')
    except r.DoesNotExist:
        print('Please run init_processes first')
        sys.exit(1)
    except Exception as e:
        print('Error: %s. Need reconstruction StaticPath instances to run')
        sys.exit(1)
    create_pipeline_plan()
    create_default_anno_methods()

if __name__ == "__main__":
    run()
