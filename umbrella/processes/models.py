from django.db import models
from django.db.models import Q
from tem.models import MsiSession, SessionPlan
from stores.models import StaticPath, Path, PathType, fill_place_holders
import sys

'''
from stores.models import DataRecord, 
class ArrayData(DataRecord):
    unit_cell_dimension
    is_stack
    sub_array_of    
'''
def getattr_from_globals(attr_name):
    # get attributes of this python module
    all_attrs = globals()
    my_attr = None
    for name, value in all_attrs.items():
        if name == attr_name:
            my_attr = value
            break
    if not my_attr:
        raise ValueError('%s not an attribute of module %s' % (attr_name, __file__))
    return my_attr

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
    name = models.CharField(max_length=32, default='aretomo3')
    version = models.CharField(max_length=32, default='2024-03-10')
    capable_tasks = models.ManyToManyField(Task,)
    callback_function = models.CharField(max_length=32, default='run_aretomo3')
    logger = models.CharField(max_length=32, default='my_log')
    #diagnosis

    def __str__(self):
        return '%s @ (%s)' % (self.name, self.version)

class PipelinePlan(models.Model):
    """
    A collection of software-defined pipe to be used together.  Commonly from start
    from one single pipe.  Other pipes would be triggered by creation of some output
    of its parent pipe.
    """
    name = models.CharField(max_length=32, default='czii-live')

    def __str__(self):
        return self.name

class Pipe(models.Model):
    name = models.CharField(max_length=32, default='voxelspacing10.000a')
    input_pipe = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, help_text='The pipe it needs to wait for input in order to run')
    software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE)
    tasks_performed = models.ManyToManyField(Task,)
    input = models.ManyToManyField(StaticPath,related_name='staticpath_in_input')
    output = models.ManyToManyField(PathType,related_name='pathtype_in_output')

    def __str__(self):
        return 'pipe %s: %s with %d tasks' % (self.name, self.software,self.tasks_performed.count())

class PipeInPlan(models.Model):
    name = models.CharField(max_length=32, default='vol001')
    plan = models.ForeignKey(PipelinePlan, on_delete=models.CASCADE)
    step = models.PositiveSmallIntegerField(default=1)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)

    def __str__(self):
        return 'plan %s pipe %s' % (self.plan, self.pipe)

    def get_replacement_map(self,proc_run=None,msi_session=None):
        mapping = {
            'proc_plan': self.plan.name,
            'pipe': self.pipe.name,
        }
        if proc_run:
            mapping['proc_run'] = proc_run.name
            mapping['proc_software'] = self.pipe.software.name
        if msi_session:
            mapping['msi_session'] = msi_session.name
            mapping['scope'] = msi_session.session_plan.scope.name
        return mapping

class GlobalParam(models.Model):
    key = models.ForeignKey(MetaKey, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(PipelinePlan, on_delete=models.CASCADE)

    def __str__(self):
        return '(%s,  %s)' % (self.pipeline, self.key)

class PipeParam(models.Model):
    key = models.ForeignKey(MetaKey, on_delete=models.CASCADE)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)
    def __str__(self):
        return '(%s, %s)' % (self.pipe, self.key)


# record
class ProcRun(models.Model):
    name = models.CharField(max_length=20, default='run001')
    proc_plan = models.ForeignKey(PipelinePlan, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)
    notes = models.TextField(max_length=255, blank=True, null=True)
    def __str__(self):
        return '%s-%s' % (self.proc_plan, self.name)

    def save_pipe_run_data(self):
        self.pipes_in_plan = PipeInPlan.objects.filter(plan=self.proc_plan)
        for pp in self.pipes_in_plan:
            p = pp.pipe
            for p_out in p.output.all():
                out_static = fill_place_holders(
                        p_out.static_path.static_path,pp.get_replacement_map(proc_run=self,msi_session=self.msi_session))
                out_overlay = fill_place_holders(
                        p_out.overlay_path,pp.get_replacement_map(proc_run=self,msi_session=self.msi_session))
                out_path = Path.objects.create(static_path=out_static,overlay_path=out_overlay)
                data_instance = RunPipeData.objects.create(
                    run=self,
                    pipe=p,
                    pathtype=p_out,
                    path=out_path,
                )

    def create_frames_runpipedata(self, msi_session):
        # frames are done in a different mechanism from others
        s = self.msi_session
        frames_fd = Frames.objects.create(
                session_plan = s.session_plan,
                frame_path = s.frames,
        )
        frames_fd.save()
        return frames_fd

    def _get_input_pipe_pk(self, pipe):
        if pipe.input_pipe:
            return pipe.input_pipe.pk
        else:
            return 0 # from msi_session acquisition

    def create_tomogram_collection(self):
        """
        Save portal schema-like record. Return True if the run adds data to these records.
        """
        tomogram_path_type_order = ['tangl','rawst','aln','ctf','rec','deno']
        run_pipe_datas = RunPipeData.objects.filter(run=self)
        pipes_input_from = []
        for pip in self.pipes_in_plan:
            if pip.pipe.input_pipe is None:
                # handle frames
                # TODO: consider doing this at the time of msi_session creation
                frames_fd = self.create_frames_runpipedata(self.msi_session)
            pipes_input_from.append(self._get_input_pipe_pk(pip.pipe))
        path_types = list(map((lambda x: x.pathtype.static_path.data_type), run_pipe_datas))
        # TODO: this makes it necessary to enter pipes in strict order.
        input_pipe_pks = pipes_input_from
        # exit if not tomogram-related
        if not set(path_types).intersection(set(tomogram_path_type_order)):
            return False
        # only get here if tomogram creation
        self.created_objects = {0:[('frames',frames_fd),]} #by pipe pk
        for ptype in tomogram_path_type_order:
            results = list(filter((lambda x: x.pathtype.static_path.data_type ==ptype), run_pipe_datas))
            for r in results:
                    my_pipe_pk = r.pipe.pk
                    saved = self._save_instance(r,input_pipe_pks)
                    if my_pipe_pk not in self.created_objects.keys():
                        self.created_objects[my_pipe_pk]=[]
                    self.created_objects[my_pipe_pk].append((ptype,saved))
        return True

    def _add_other_objects(self, class_name, my_pipe):
        """ TODO: These need to be reworked into adding real values
        """
        results = PipeInPlan.objects.filter(plan=self.proc_plan,pipe=my_pipe)
        if not results:
            raise ValueError('pipe %s not in plan of this run' % (my_pipe))
        # TODO what if a pipe is used twice like step 2 and 3 ?
        my_pipe_step = results[0].step
        my_pipe_pk = my_pipe.pk
        if class_name == 'Tomograms':
            ### TODO Really determine voxel and pixel spacings###
            if my_pipe_step == 1:
                voxels = TomogramVoxelSpacing.objects.filter(spacing=5.0)
                voxel = voxels[0]
            elif my_pipe_step in (2,3,4):
                voxels = TomogramVoxelSpacing.objects.filter(spacing=10.0)
                voxel = voxels[0]
            else:
                voxel = None
            if voxel:
                self.created_objects[my_pipe_pk].append(('vox',voxel))
            ### TODO Define recon method in pipe
            recon_methods = ReconMethod.objects.all()
            if not recon_methods:
                # Create default recon method
                recon_method = ReconMethod.objects.create()
            else:
                recon_method = recon_methods[0]
            self.created_objects[my_pipe_pk].append(('recmethod',recon_method))
            self.created_objects[my_pipe_pk].append(('msi',self.msi_session))

    def is_recon_ctf_deconvolved(self, pipe):
        '''
        Determine if ctf deconvolution is done in this pipe.
        '''
        if pipe is None:
            return False
        task_names = list(map((lambda x: x.name),pipe.tasks_performed.all()))
        output_types = list(map((lambda x: x.static_path.data_type),pipe.output.all()))
        input_types = list(map((lambda x: x.data_type),pipe.input.all()))
        input_pipe = pipe.input_pipe
        if 'ctf deconvolution' in task_names:
            return True
        if set(['rec','deno','evn','odd']).intersection(output_types):
            if 'aln' in input_types and 'ctf' not in input_types:
                # alignment is an input but not ctf
                return False
            if input_pipe is not None:
                # determined by input_pipe
                return self.is_recon_ctf_deconvolved(input_pipe)
        return False

    def _save_instance(self, pdata, input_pipe_pks):
        """
        Save tomogram-related reinstances
        """
        model_map = {   
                        # PathType.static_name: (class name, attribute name in other classes)
                        'frames':('Frames', 'frames'),
                        'rawst':('RawTiltSeries','tiltseries'),
                        'tangl':('TiltAngles','angles'),
                        'aln':('Alignment','alignment'),
                        'ctf':('Ctf','ctf'),
                        'recmethod':('ReconMethod','recon_method'),
                        'vox':('TomogramVoxelSpacing','voxel_spacing'),
                        'rec':('Tomograms','tomograms'),
                        'deno':('Tomograms','tomograms'),
                        'msi':('MsiSession','msi_session'),
                    }
        all_input_pipe_pks = list(input_pipe_pks)
        ptype = pdata.pathtype.static_path.data_type
        class_name = model_map[ptype][0]
        my_attr = getattr_from_globals(class_name)
        my_instance = my_attr(pipe_data=pdata)
        my_field_names = list(map((lambda x:x.name),my_instance._meta.fields))
        my_pipe = pdata.pipe
        my_pipe_pk = my_pipe.pk
        if my_pipe_pk not in self.created_objects.keys():
            all_input_pipe_pks.append(my_pipe_pk)
            self.created_objects[my_pipe_pk]=[]
        self._add_other_objects(class_name, pdata.pipe)
        #
        my_input_pipe = self._get_input_pipe_pk(my_pipe)
        for i in range(all_input_pipe_pks.index(my_input_pipe)+1):
            pk = all_input_pipe_pks[i]
            for item in self.created_objects[pk]:
                k, obj = item
                attr_name = model_map[k][1]
                if attr_name in my_field_names:
                    if attr_name=='ctf':
                        # Without ctf input means the output tomogram is not ctf deconvoluted..
                        if not self.is_recon_ctf_deconvolved(my_pipe):
                            continue
                    setattr(my_instance, attr_name, obj)
                if ptype == 'deno' and k == 'rec':
                    # tomogram is derived from others
                    setattr(my_instance,'parent_tomo', obj)
        for item in self.created_objects[my_pipe_pk]:
            k, obj = item
            if model_map[k][1] in my_field_names:
                 setattr(my_instance, model_map[k][1], obj)
        # specific to denoised tomogram
        if ptype == 'deno':
            deno_methods = TomoPostProcessMethod.objects.filter(software=pdata.pipe.software)
            if not deno_methods:
                # Create default method. TODO: should specify names
                deno_method = TomoPostProcessMethod.objects.create(software=pdata.pipe.software)
            else:
                deno_method = deno_methods[0]
            setattr(my_instance,'post_process', deno_method)
        my_instance.save()
        return my_instance

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
    '''
    Output data path record of the processing run
    '''
    run = models.ForeignKey(ProcRun, on_delete=models.CASCADE)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)
    path = models.ForeignKey(Path, on_delete=models.CASCADE, null=True)
    pathtype = models.ForeignKey(PathType, on_delete=models.CASCADE)

    def __str__(self):
        return '%s %s: %s' % (self.run, self.pipe.name, self.path)

# models to record the final relationship. Path should have everything except tomo_run
class TiltAngles(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)

class Frames(models.Model):
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    frame_path = models.ForeignKey(Path, related_name='processing_frame_path',on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.frame_path)

class RawTiltSeries(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    angles = models.ForeignKey(TiltAngles, on_delete=models.CASCADE)
    frames = models.ForeignKey(Frames, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

class Ctf(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    tiltseries = models.ForeignKey(RawTiltSeries, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

class Alignment(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    tiltseries = models.ForeignKey(RawTiltSeries, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

class TomogramVoxelSpacing(models.Model):
    spacing = models.FloatField(default=10.0, help_text='uniform voxel spacing in angstroms')

    def __str__(self):
        return '%.3f' % (self.spacing)

class ReconMethod(models.Model):
    name = models.CharField(max_length=32, default='weighted back projection')

    def __str__(self):
        return '%s' % (self.name)

class TomoPostProcessMethod(models.Model):
    name = models.CharField(max_length=32, default='denoised')
    software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = [["name","software"]]

    def __str__(self):
        return '%s by %s' % (self.name, self.software)

class Tomograms(models.Model):
    '''
    Tomogram collection within the msi_session
    '''
    # This allows denoise or other type of tomograms to be included
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    recon_method = models.ForeignKey(ReconMethod, on_delete=models.CASCADE)
    voxel_spacing = models.ForeignKey(TomogramVoxelSpacing, on_delete=models.CASCADE)
    alignment = models.ForeignKey(Alignment, on_delete=models.CASCADE)
    ctf = models.ForeignKey(Ctf, on_delete=models.CASCADE, null=True, blank=True)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query
    post_process = models.ForeignKey(TomoPostProcessMethod, on_delete=models.SET_NULL, null=True, blank=True)
    parent_tomo = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

def suggest_name(prefix, msi_session, plan, model_name='ProcRun'):
    """
    Make unique name by advancing to next integer.
    """
    model_instance = getattr(sys.modules[__name__], model_name)
    if prefix:
        prefix_search = prefix
        old_runs = model_instance.objects.filter(Q(name__startswith=prefix_search), proc_plan=plan, msi_session=msi_session)
        used_names = list(map((lambda x: x.name), old_runs))
        if not used_names:
            # first session of the day
            return prefix_search + '%03d' % 1
        used_numbers = list(map((lambda x: int(x.split(prefix_search)[-1])), used_names))
        return '%s%03d' % (prefix,max(used_numbers)+1)
    else: 
        raise ValueError('Prefix must not be empty string for run name')
