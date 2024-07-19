from django.contrib.auth.models import User
import sys
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
from tem.models import *
from stores.models import StaticPath,PathType, fill_place_holders
from processes.models import ProcSoftware,Task, PipelinePlan, PlanPipe, ReconMethod, TomogramVoxelSpacing

def _get_first_of(model_class):
    return model_class.objects.get(pk=1)

def create_static_path(data_type):
    for data_type in ['tangl','rawst','aln','ctf','rec','evn','odd','deno']:
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{proc_software}/{proc_run}/{msi_session}/{run}/%s/{proc_software/{proc_run}/{pipe}/' % data_type,
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
    task_names = ['motion correction',
                    'stack tilt series',
                    'ctf estimation',
                    'align tilt series',
                    'ctf decovolution',
                    'full tomo reconstruction',
                    'even/odd frame tomo reconstruction',
                    'denoised reconstruction',
    ]
    tasks = []
    for i, n in enumerate(task_names):
        tasks.append(Task.objects.create(name=n, step=i+1))
    return tasks

def create_pipeline_plan():
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
    plan_pipe1 = PlanPipe.objects.create(name='vol001',plan=plan,step=1,software=aretomo3)
    # AreTomo3-10A recon
    plan_pipe2 = PlanPipe.objects.create(name='vol002',plan=plan,step=2,software=aretomo3)
    plan_pipe3 = PlanPipe.objects.create(name='vol003',plan=plan,step=3,software=aretomo3)
    plan_pipe4 = PlanPipe.objects.create(name='run001',plan=plan,step=4,software=denoiser)
    #input
    input_path_types = []
    #PathType may not be good enough to tell different software
    # TODO: make input only specify static_path, not PathType with software definition
    #output
    output_path_types = []
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('tangl'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{run}.rawtlt',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('rawst'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{run}_rawtilts.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('ctf'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{run}_CTF.txt',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('aln'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{run}.aln',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('rec'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{run}_Vol.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('evn'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{run}_EVN_Vol.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('odd'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{run}_ODD_Vol.mrc',
    ))
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('deno'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{input_pipe}/{run}_Vol.mrc',
    ))
    for t in tasks[:-1]:
        # everything at 5 Å except denoising
        plan_pipe1.tasks_performed.add(t)
    for t in tasks[-3:-2]:
        # 10Å no CTF WBP
        plan_pipe2.tasks_performed.add(t)
    for t in tasks[-3:-2]:
        # 10Å no CTF SART
        plan_pipe3.tasks_performed.add(t)
    for t in tasks[-1:]:
        plan_pipe4.tasks_performed.add(t)
    # input/output
    plan_pipe1.input.add(get_static_path('frames'))
    plan_pipe1.input.add(get_static_path('mdoc'))
    for p in output_path_types[:-1]:
        # all except denoise
        plan_pipe1.output.add(p) 
    plan_pipe2.input.add(get_static_path('tangl'))
    plan_pipe2.input.add(get_static_path('aln'))
    plan_pipe2.input.add(get_static_path('rawst'))
    plan_pipe3.input.add(get_static_path('tangl'))
    plan_pipe3.input.add(get_static_path('aln'))
    plan_pipe3.input.add(get_static_path('rawst'))
    for p in output_path_types[4:5]: #recon
       plan_pipe2.output.add(p)
       plan_pipe3.output.add(p)
    plan_pipe4.input.add(get_static_path('odd'))
    plan_pipe4.input.add(get_static_path('evn'))
    for p in output_path_types[-1:]:
       plan_pipe4.output.add(p)
    # where the input are from
    plan_pipe1.input_pipe_step = 0
    plan_pipe2.input_pipe_step = 1
    plan_pipe3.input_pipe_step = 1
    plan_pipe4.input_pipe_step = 1
    # save
    plan_pipe1.save()
    plan_pipe2.save()
    plan_pipe3.save()
    plan_pipe4.save()

def create_default_spacings():
    TomogramVoxelSpacing.objects.create(spacing=5.0) 
    TomogramVoxelSpacing.objects.create(spacing=10.0) 

def create_default_recon_methods():
    ReconMethod.objects.create(name='weighted back projection')
    ReconMethod.objects.create(name='SART')
    ReconMethod.objects.create(name='SIRT')

def run():
    try:
        r = get_static_path('frames')
    except r.DoesNotExist:
        print('Please run init first')
        sys.exit(1)
    except Exception as e:
        print('Error: %s. Need frames and mdoc StaticPath instances to run')
        sys.exit(1)
    create_pipeline_plan()
    create_default_spacings()
    create_default_recon_methods()

if __name__ == "__main__":
    run()
