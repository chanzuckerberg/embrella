from django.contrib.auth.models import User
import sys
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
from tem.models import *
from stores.models import StaticPath,PathType, fill_place_holders
from processes.models import ProcSoftware,Task, ProcPlan, Pipe, PipeInPlan, ReconMethod, TomogramVoxelSpacing
from processes.models import PipeJoint, AnnotationMethod

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

def add_pipe_joints(pipe_in_plan, input_pipe_in_plan, data_types):
    pathtypes_in_input = input_pipe_in_plan.pipe.output.all()
    dtypes = list(map((lambda x:x.static_path.data_type), pathtypes_in_input))
    for t in data_types:
        dindex = dtypes.index(t)
        input_pathtype = pathtypes_in_input[dindex]
        PipeJoint.objects.create(
                pipe_in_plan=pipe_in_plan,
                input_pipe_in_plan=input_pipe_in_plan,
                input_pathtype=input_pathtype)

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
    membr = ProcSoftware.objects.create(name='membraneseg',
                version='2024-03-10')
    for t in tasks[0:1]:
        pytom.capable_tasks.add(t)
    for t in tasks[1:2]:
        gallery.capable_tasks.add(t)
    for t in tasks[2:3]:
        membr.capable_tasks.add(t)
    plan1 = ProcPlan.objects.create(name='pytom-pick')
    plan2 = ProcPlan.objects.create(name='galery-pick')
    plan3 = ProcPlan.objects.create(name='membraneseg')
    # pipes
    pipe1 = Pipe.objects.create(name='80s-ribosome',software=pytom)
<<<<<<< HEAD
    pipe2 = Pipe.objects.create(name='gallery',software=gallery) #or  name=gallery, software=slabpick,
    pipe3 = Pipe.objects.create(name='membrane',software=membr) #a pipe and a datatype??
    # AreTomo3-5A recon
    plan_pipe1 = PipeInPlan.objects.create(name='pick1',plan=plan,step=1,pipe=pipe1)
    # AreTomo3-10A recon
    plan_pipe2 = PipeInPlan.objects.create(name='pick2',plan=plan,step=2,pipe=pipe2)
=======
    pipe2 = Pipe.objects.create(name='gallery',software=gallery)
    pipe3 = Pipe.objects.create(name='membrane',software=membr)
    # PyTom
    plan1_pipe1 = PipeInPlan.objects.create(name='pick1',plan=plan1,step=1,pipe=pipe1)
    # Gallery
    plan2_pipe2 = PipeInPlan.objects.create(name='galr1',plan=plan2,step=1,pipe=pipe2)
    # Membrane segamentation
    plan3_pipe3 = PipeInPlan.objects.create(name='mask1',plan=plan3,step=1,pipe=pipe3)
>>>>>>> origin/main
    #input
    input_path_types = []
    #output
    output_path_types = []
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('pick'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{proc_run}/{run}/output.txt',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('galr'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{proc_run}/{run}/output.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('seg'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{proc_run}/{run}/output.mrc',
    ))
    for t in tasks[0:1]:
        # picking ribosome
        pipe1.tasks_performed.add(t)
    for t in tasks[1:2]:
        # gallery making
        pipe2.tasks_performed.add(t)
    for t in tasks[2:3]:
        # membrane
        pipe3.tasks_performed.add(t)
    # input/output
    for p in output_path_types[0:1]:
        pipe1.output.add(p) 
    for p in output_path_types[1:2]: #recon
       pipe2.output.add(p)
    for p in output_path_types[2:3]:
       pipe3.output.add(p)
    # where the input are from
    input_rec = Pipe.objects.filter(name='vol002')[0]
    pipe1.input.add(get_static_path('rec')) # pick
    pipe2.input.add(get_static_path('pick')) # gallery
    pipe2.input.add(get_static_path('deno')) # gallery
    pipe3.input.add(get_static_path('rec')) # seg
    # save
    pipe1.save()
    pipe2.save()
    pipe3.save()

    plan_live = ProcPlan.objects.get(pk=1)
    plan_deno = ProcPlan.objects.get(pk=2)
    plan_live_v001 = PipeInPlan.objects.filter(plan=plan_live,pipe__name='vol001')[0]
    plan_deno_den001 = PipeInPlan.objects.filter(plan=plan_deno,pipe__name='den001')[0]
    add_pipe_joints(plan1_pipe1, plan_live_v001,['rec'])
    add_pipe_joints(plan2_pipe2, plan_deno_den001,['deno'])
    add_pipe_joints(plan2_pipe2, plan1_pipe1,['pick'])
    add_pipe_joints(plan3_pipe3, plan_live_v001,['rec'])

def create_default_anno_methods():
    AnnotationMethod.objects.create(name='template matching')
    AnnotationMethod.objects.create(name='ml semantic segmentation')

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
