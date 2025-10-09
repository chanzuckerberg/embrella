from django.contrib.auth.models import User
import sys
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
from tem.models import *
from stores.models import StaticPath,PathType, fill_place_holders
from processes.models import ProcSoftware,Task, ProcPlan, Pipe, PipeInPlan, ReconMethod, TomogramVoxelSpacing
from processes.models import PipeJoint

def _get_first_of(model_class):
    return model_class.objects.get(pk=1)

def create_static_path(data_type):
    for data_type in ['cpck','ocpi']:
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
    task_names = ['create copick project',
                    'run octopi',
    ]
    current_tasks = Task.objects.all()
    task_count = len(current_tasks)
    tasks = []
    for i, n in enumerate(task_names):
        tasks.append(Task.objects.create(name=n, step=i+task_count+1))
    return tasks

def create_pipeline_plan():
    tasks = createStandardTasks()
    copick = ProcSoftware.objects.create(name='copick',
                version='version in .json')
    octopi = ProcSoftware.objects.create(name='octopi',
                version='version in .json')

    for t in tasks[0:1]:
        copick.capable_tasks.add(t)
    for t in tasks[1:2]:
        octopi.capable_tasks.add(t)
    plan1 = ProcPlan.objects.create(name='czii-copick')
    plan2 = ProcPlan.objects.create(name='czii-octopi')
    # pipes
    pipe1 = Pipe.objects.create(name='cpck_j1', software=copick)
    pipe2 = Pipe.objects.create(name='octopi_j2', software=octopi)

    plan1_pipe1 = PipeInPlan.objects.create(name='copick-step',plan=plan1,step=1,pipe=pipe1)
    plan2_pipe2 = PipeInPlan.objects.create(name='octopi-step',plan=plan2,step=1,pipe=pipe2)

    #input
    input_path_types = []
    #output
    output_path_types = []
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('cpck'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('ocpi'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/',
    ))
    for t in tasks[0:1]:
        # copick project creation
        pipe1.tasks_performed.add(t)
    for t in tasks[1:2]:
        # run octopi
        pipe2.tasks_performed.add(t)

    # input/output
    for p in output_path_types[0:1]:
        pipe1.output.add(p) 
    for p in output_path_types[1:2]: #recon
       pipe2.output.add(p)

    pipe1.input.add(get_static_path('rec'))   
    pipe2.input.add(get_static_path('rec')) 

    # pipe joints
    plan_cpck = ProcPlan.objects.get(pk=1)
    plan_ocpi = ProcPlan.objects.get(pk=2)

    plan_cpck_j1 = PipeInPlan.objects.filter(plan=plan_cpck, pipe__name='cpck_j1').first()
    plan_ocpi_j2 = PipeInPlan.objects.filter(plan=plan_ocpi, pipe__name='octopi_j2').first()


    producer_rec = PipeInPlan.objects.filter(
        pipe__output__static_path__data_type='rec'
    ).first()

    if producer_rec:
        add_pipe_joints(plan1_pipe1, producer_rec, ['rec'])  # copick consumes 'rec'
        add_pipe_joints(plan2_pipe2, producer_rec, ['rec'])  # octopi consumes 'rec'
    else:
        print("⚠️ No upstream PipeInPlan found that outputs 'rec'")


def run():
    try:
        r = get_static_path('rec')
    except StaticPath.DoesNotExist:
        print('Please run init_processes first')
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}. Need reconstruction StaticPath instances to run')
        sys.exit(1)
    create_pipeline_plan()

if __name__ == "__main__":
    run()
