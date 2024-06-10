from django.contrib.auth.models import User
import sys
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
from tem.models import *
from stores.models import StaticPath,PathType, fill_place_holders
from processes.models import ProcSoftware,Task, PipelinePlan, PlanPipe

def _get_first_of(model_class):
    return model_class.objects.get(pk=1)

def create_static_path(data_type):
    for data_type in ['rawst','tangl','ctf','aln','rec','evn','odd','deno']:
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{proc_software}/{proc_run}/{session}/{run}/%s' % data_type,
        )
    return instance

def get_static_path(data_type):
    qset = StaticPath.objects.filter(data_type=data_type)
    if qset:
        return qset[0]
    else:
        return create_static_path(data_type)

def createStandardTasks():
    task_names = ['motion correction',
                    'stack tilt series',
                    'ctf estimation',
                    'ctf decovolution',
                    'align tilt series',
                    'full tomo reconstruction',
                    'even/odd frame tomo reconstruction',
                    'denoised reconstruction',
    ]
    tasks = []
    for i, n in enumerate(task_names):
        tasks.append(Task.objects.create(name=n, step=i+1))
    return tasks

def createPipelinePlan():
    tasks = createStandardTasks()
    aretomo3 = ProcSoftware.objects.create(name='aretomo3',
                version='2024-03-10')
    denoiser = ProcSoftware.objects.create(name='denoise',
                version='2024-03-10')
    for t in tasks[:-1]:
        aretomo3.capable_tasks.add(t)
    for t in tasks[-1:]:
        denoiser.capable_tasks.add(t)
    plan = PipelinePlan.objects.create(name='czii-live')
    # AreTomo3-5A recon
    plan_pipe1 = PlanPipe.objects.create(name='voxelspacing10.000a_wbp',plan=plan,step=1,software=aretomo3)
    # AreTomo3-10A recon
    plan_pipe2 = PlanPipe.objects.create(name='voxelspacing5.000a_dctf',plan=plan,step=2,software=aretomo3)
    plan_pipe3 = PlanPipe.objects.create(name='voxelspacing5.000a_dctf',plan=plan,step=3,software=denoiser)
    #input
    input_path_types = []
    #PathType may not be good enough to tell different software
    # TODO: make input only specify static_path, not PathType with software definition
    #output
    output_path_types = []
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('rawst'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{run}_rawtilts.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('ctf'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{run}_CTF.txt',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('aln'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{run}.aln',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('rec'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{pipe}/{run}_Vol.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('evn'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{pipe}/{run}_EVN_Vol.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('odd'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{pipe}/{run}_ODD_Vol.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('deno'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{session}/{input_pipe}/{run}_Vol.mrc',
    ))
    for t in tasks[:-2]:
        if 'decovolution' not in t.name:
            plan_pipe1.tasks_performed.add(t)
    for t in tasks[-5:-1]:
        if 'align tilt series' not in t.name:
            plan_pipe2.tasks_performed.add(t)
    for t in tasks[-1:]:
        plan_pipe3.tasks_performed.add(t)
    # input/output
    plan_pipe1.input.add(get_static_path('frames'))
    plan_pipe1.input.add(get_static_path('mdoc'))
    for p in output_path_types[:-3]:
       plan_pipe1.output.add(p) 
    plan_pipe2.input.add(get_static_path('ctf'))
    plan_pipe2.input.add(get_static_path('tangl'))
    plan_pipe2.input.add(get_static_path('aln'))
    plan_pipe2.input.add(get_static_path('rawst'))
    for p in output_path_types[-3:-1]:
       plan_pipe2.output.add(p)
    plan_pipe3.input.add(get_static_path('odd'))
    plan_pipe3.input.add(get_static_path('evn'))
    for p in output_path_types[-1:]:
       plan_pipe3.output.add(p)
    plan_pipe1.save()
    plan_pipe2.save()
    plan_pipe3.save()
 
def run():
    try:
        r = get_static_path('frames')
    except r.DoesNotExist:
        print('Please run init first')
        sys.exit(1)
    except Exception as e:
        print('Error: %s. Need frames and mdoc StaticPath instances to run')
        sys.exit(1)
    createPipelinePlan()

if __name__ == "__main__":
    run()
