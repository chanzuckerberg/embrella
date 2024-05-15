from django.db import models
from tem.models import Session
from stores.models import StaticPath, PathType, Path
'''
from stores.models import DataRecord, 
class ArrayData(DataRecord):
    unit_cell_dimension
    is_stack
    sub_array_of    
'''
class MetaKey(models.Model):
    """
    Goes into stores.Version.metadata
    """
    name = models.CharField(max_length=32, default='cs')
    definition = models.TextField(max_length=255, default='Spherical aberration constant')
    unit = models.CharField(max_length=32, default='mm')
    data_type = models.CharField(max_length=6, default='float',help_text='python type')

    def __str__(self):
       return '%s in unit of %s' % (self.name, self.unit)

'''
PathData
    name
    variables
    pattern
'''

class Task(models.Model):
    name = models.CharField(max_length=32, default='motion correction')
    step = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return '%d-%s' % (self.step,self.name)

class ProcSoftware(models.Model):
    name = models.CharField(max_length=32, default='AreTomo3')
    version = models.CharField(max_length=32, default='2024-03-10')
    capable_tasks = models.ManyToManyField(Task,)
    callback_function = models.CharField(max_length=32, default='run_aretomo3')
    logger = models.CharField(max_length=32, default='my_log')
    #diagnosis

    def __str__(self):
        return '%s @ (%s)' % (self.name, self.version)

class PipelinePlan(models.Model):
    name = models.CharField(max_length=32, default='czii-live')

    def __str__(self):
        return self.name

class PlanPipe(models.Model):
    plan = models.ForeignKey(PipelinePlan, on_delete=models.CASCADE)
    step = models.PositiveSmallIntegerField(default=1)
    software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE)
    tasks_performed = models.ManyToManyField(Task,)
    input = models.ManyToManyField(StaticPath,related_name='staticpath_in_input')
    output = models.ManyToManyField(PathType,related_name='pathtype_in_output')


    def __str__(self):
        return 'plan %s pipe %d: %s with %d tasks' % (self.plan, self.step, self.software,self.tasks_performed.count())

class GlobalParam(models.Model):
    key = models.ForeignKey(MetaKey, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(PipelinePlan, on_delete=models.CASCADE)

    def __str__(self):
        return '(%s,  %s)' % (self.pipeline, self.key)

class PipeParam(models.Model):
    key = models.ForeignKey(MetaKey, on_delete=models.CASCADE)
    pipe = models.ForeignKey(PlanPipe, on_delete=models.CASCADE)
    def __str__(self):
        return '(%s, %s)' % (self.pipe, self.key)


# record
class ProcRun(models.Model):
    name = models.CharField(max_length=20, default='1')
    proc_plan = models.ForeignKey(PipelinePlan, on_delete=models.CASCADE)
    tomo_session = models.ForeignKey(Session, on_delete=models.CASCADE)
    notes = models.TextField(max_length=255, blank=True, null=True)
    def __str__(self):
        return '%s-%s' % (self.proc_plan, self.name)

class RunGlobalValue(models.Model):
    run = models.ForeignKey(ProcRun, on_delete=models.CASCADE)
    param = models.ForeignKey(GlobalParam, on_delete=models.CASCADE)
    value = models.CharField(max_length=255, default='100')
    def __str__(self):
        if self.value and self.param.key.data_type in ('dir','file'):
            display_value = Path.objects.get(pk=int(self.value))
        else:
            display_value = self.value
        return '%s : %s' % (self.param.key.name,display_value)

class RunPipeValue(models.Model):
    run = models.ForeignKey(ProcRun, on_delete=models.CASCADE)
    param = models.ForeignKey(PipeParam, on_delete=models.CASCADE)
    value = models.CharField(max_length=255, default='100')

    def __str__(self):
        if self.value and self.param.key.data_type in ('dir','file'):
            display_value = Path.objects.get(pk=int(self.value))
        else:
            display_value = self.value
        return 'pipe%d %s : %s' % (self.param.pipe.step, self.param.key.name,display_value)

class RunPipeData(models.Model):
    run = models.ForeignKey(ProcRun, on_delete=models.CASCADE)
    pipe = models.ForeignKey(PlanPipe, on_delete=models.CASCADE)
    path = models.ForeignKey(Path, on_delete=models.CASCADE, null=True)

