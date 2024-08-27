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
    for data_type in ['tangl','rawst','aln','ctf','rec','evn','odd','deno']:
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
    task_names = ['motion correction',
                    'stack tilt series',
                    'ctf estimation',
                    'align tilt series',
                    'ctf deconvolution',
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
    denoiser = ProcSoftware.objects.create(name='denoiset',
                version='2024-03-10')
    for t in tasks[:-1]:
        aretomo3.capable_tasks.add(t)
    for t in tasks[-1:]:
        denoiser.capable_tasks.add(t)
    plan1 = ProcPlan.objects.create(name='czii-live')
    plan2 = ProcPlan.objects.create(name='czii-denoise')
    # AreTomo3-5A recon
    pipe1 = Pipe.objects.create(name='vol001',software=aretomo3)
    # AreTomo3-10A recon
    pipe2 = Pipe.objects.create(name='vol002',software=aretomo3)
    pipe3 = Pipe.objects.create(name='vol003',software=aretomo3)
    pipe4 = Pipe.objects.create(name='den001',software=denoiser) ##deno should be a 5A recon
    # AreTomo3-5A recon
    plan1_pipe1 = PipeInPlan.objects.create(name='vol001',plan=plan1,step=1,pipe=pipe1)
    # AreTomo3-10A recon
    plan1_pipe2 = PipeInPlan.objects.create(name='vol002',plan=plan1,step=2,pipe=pipe2)
    plan1_pipe3 = PipeInPlan.objects.create(name='vol003',plan=plan1,step=3,pipe=pipe3)
    plan2_pipe4 = PipeInPlan.objects.create(name='den001',plan=plan2,step=1,pipe=pipe4)
    #input
    input_path_types = []
    #PathType may not be good enough to tell different software
    # TODO: make input only specify static_path, not PathType with software definition
    #output
    output_path_types = []
    output_path_types.append(PathType.objects.create(
                static_path=get_static_path('tangl'),
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{proc_run}/{msi_session}/{run}.rawtlt',
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
                overlay_path='/hpc/processing/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{run}_Vol.mrc',
    ))
    for t in tasks[:-1]:
        # everything at 5 Å except denoising
        pipe1.tasks_performed.add(t)
    for t in tasks[-3:-2]:
        # 10Å no CTF WBP
        pipe2.tasks_performed.add(t)
    for t in tasks[-3:-2]:
        # 10Å no CTF SART
        pipe3.tasks_performed.add(t)
    for t in tasks[-1:]:
        pipe4.tasks_performed.add(t)
    # input/output
    pipe1.input.add(get_static_path('frames'))
    pipe1.input.add(get_static_path('mdoc'))
    for p in output_path_types[:-1]:
        # all except denoise
        pipe1.output.add(p) 
    pipe2.input.add(get_static_path('tangl'))
    pipe2.input.add(get_static_path('aln'))
    pipe2.input.add(get_static_path('rawst'))
    pipe3.input.add(get_static_path('tangl'))
    pipe3.input.add(get_static_path('aln'))
    pipe3.input.add(get_static_path('rawst'))
    for p in output_path_types[4:5]: #recon
       pipe2.output.add(p)
       pipe3.output.add(p)
    pipe4.input.add(get_static_path('rec')) # denoise
    for p in output_path_types[-1:]:
       pipe4.output.add(p)
    # save
    pipe1.save()
    pipe2.save()
    pipe3.save()
    pipe4.save()

    add_pipe_joints(plan1_pipe2, plan1_pipe1,['rawst','tangl','aln'])
    add_pipe_joints(plan1_pipe3, plan1_pipe1,['rawst','tangl','aln'])
    add_pipe_joints(plan2_pipe4, plan1_pipe1,['rec',])

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
