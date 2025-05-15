from django.db import models
from django.db.models import Q
from tem.models import MsiSession, SessionPlan
from stores.models import StaticPath, Path, PathType, fill_place_holders
import sys
import uuid


from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now


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
    name = models.CharField(max_length=255, default='motion correction')
    step = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return '%d-%s' % (self.step,self.name)

class ProcSoftware(models.Model):
    """
    A software program started with the same command with different options.
    """
    name = models.CharField(max_length=32, default='aretomo3')
    version = models.CharField(max_length=32, default='2024-03-10')
    capable_tasks = models.ManyToManyField(Task,)
    callback_function = models.CharField(max_length=32, default='run_aretomo3')
    logger = models.CharField(max_length=32, default='my_log')
    #diagnosis

    def __str__(self):
        return '%s @ (%s)' % (self.name, self.version)

class ProcPlan(models.Model):
    """
    A plan for running a single software and producing outputs based on the
    pipes in the plan.
    """
    name = models.CharField(max_length=32, default='czii-live')

    def __str__(self):
        return self.name

class Pipe(models.Model):
    """
    A subset of tasks performed by the software that leads to distinguishable outputs
    in the same plan.
    """
    name = models.CharField(max_length=32, default='voxelspacing10.000a')
    software = models.ForeignKey(ProcSoftware, on_delete=models.CASCADE)
    tasks_performed = models.ManyToManyField(Task,)
    input = models.ManyToManyField(StaticPath,related_name='staticpath_in_input')
    output = models.ManyToManyField(PathType,related_name='pathtype_in_output')

    def __str__(self):
        return 'pipe %s using %s' % (self.name, self.software.name)

class PipeInPlan(models.Model):
    """
    The pipes executed in a plan.
    """
    name = models.CharField(max_length=32, default='vol001')
    plan = models.ForeignKey(ProcPlan, on_delete=models.CASCADE)
    step = models.PositiveSmallIntegerField(default=1)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)

    def __str__(self):
        return '[%s] %s' % (self.plan, self.pipe)

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

class PipeJoint(models.Model):
    """
    Joint to connect a pipe needing input with an output static path of another pipe.
    This format allows multiple single direction inputs to be defined on pipes.
    """
    pipe_in_plan = models.ForeignKey(PipeInPlan, related_name='plan_of_pipe', on_delete=models.CASCADE, help_text='Relates where the pipt is that needing input is in its plan')
    input_pipe_in_plan = models.ForeignKey(PipeInPlan, related_name='plan_of_input_pipe', on_delete=models.CASCADE, help_text='Relates where the pipe is used as input is in its plan')
    input_pathtype = models.ForeignKey(PathType, null=True, blank=True, on_delete=models.SET_NULL, help_text='The output pathtype from input_pipe used as the input')

    def __str__(self):
        return '%s needs %s from %s' % (self.pipe_in_plan, self.input_pathtype.static_path.data_type, self.input_pipe_in_plan)

class GlobalParam(models.Model):
    key = models.ForeignKey(MetaKey, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(ProcPlan, on_delete=models.CASCADE)

    def __str__(self):
        return '(%s,  %s)' % (self.pipeline, self.key)

class PipeParam(models.Model):
    key = models.ForeignKey(MetaKey, on_delete=models.CASCADE)
    pipe = models.ForeignKey(Pipe, on_delete=models.CASCADE)
    def __str__(self):
        return '(%s, %s)' % (self.pipe, self.key)


# record
class ProcRun(models.Model):
    """
    A single execution of a processing plan. It gives a json file describing the
    options used.  All output are saved under the rundir.
    """
    name = models.CharField(max_length=20, default='run001')
    proc_plan = models.ForeignKey(ProcPlan, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE)
    notes = models.TextField(max_length=255, blank=True, null=True)
    json_path = models.ForeignKey(Path, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return '%s-%s' % (self.proc_plan, self.name)

    def save_pipe_run_data(self):
        """
        Creation of ProcRun instance triggers saving of pipe_run_data which are
        output data of the run.
        """
        self.pipes_in_plan = PipeInPlan.objects.filter(plan=self.proc_plan)
        for pp in self.pipes_in_plan:
            p = pp.pipe
            for p_out in p.output.all():
                # create pipe_run_data for each of the output.
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
        """
        Frames are input of the first processing. This method creates its record.
        """
        # frames are done in a different mechanism from others
        s = self.msi_session
        frames_fd = Frames.objects.create(
                session_plan = s.session_plan,
                msi_session = s,
                frame_path = s.frames,
        )
        frames_fd.save()
        return frames_fd

    def _get_pipe_joints(self, pipe):
        joints = PipeJoint.objects.filter(pipe_in_plan__pipe=pipe)
        return joints

    def _get_input_pipe_pks(self, pipe):
        joints = self._get_pipe_joints(pipe)
        input_pipes = list(set(map((lambda x: x.input_pipe_in_plan.pipe),joints)))
        print(input_pipes)
        pks = list(set(map((lambda x:x.pk), input_pipes)))
        if not pks:
            return [0,] # from msi_session acquisition
        return pks

    def create_tomogram_collection(self, input_objects={}):
        """
        Save data-portal schema-like record. Return True if the run adds data to these records.
        """
        tomogram_path_type_order = ['tangl','rawst','aln','ctf','rec','deno','seg','pick','galr']
        run_pipe_datas = RunPipeData.objects.filter(run=self)
        pipes_input_from = []
        frames_fd = None
        for pipl in self.pipes_in_plan:
            if not self._get_pipe_joints(pipl.pipe):
                # handle frames
                # TODO: consider doing this at the time of msi_session creation
                frames_fd = self.create_frames_runpipedata(self.msi_session)
            pipes_input_from.extend(self._get_input_pipe_pks(pipl.pipe))
        path_types = list(map((lambda x: x.pathtype.static_path.data_type), run_pipe_datas))
        # TODO: this makes it necessary to enter pipes in strict order.
        input_pipe_pks = pipes_input_from
        print('all input pipe pks', input_pipe_pks)
        if input_objects:
            tomo_input = input_objects['tomo']
            pick_input = input_objects['pick']
        else:
            tomo_input = False
            pick_input = False
        if not tomo_input:
            if frames_fd:
                # processing run starts from frames
                self.created_objects = {0:[('frames',frames_fd),]} #by pipe pk
        else:
            # processing run starts from tomogram
            pipe_pk = tomo_input.pipe_data.pipe.pk
            ptype = tomo_input.pipe_data.pathtype.static_path.data_type
            self.created_objects = {pipe_pk:[(ptype,tomo_input),]}
            input_pipe_pks = [tomo_input.pipe_data.pipe.pk,]
            if pick_input:
                # processing run needing pick_input such as 2d gallery making
                pipe_pk = pick_input.pipe_data.pipe.pk
                ptype = pick_input.pipe_data.pathtype.static_path.data_type
                self.created_objects[pipe_pk] = [(ptype,pick_input),]
                input_pipe_pks.append(pick_input.pipe_data.pipe.pk)
            
        input_objects = {}
        # accumulate created_objects
        for ptype in tomogram_path_type_order:
            results = list(filter((lambda x: x.pathtype.static_path.data_type ==ptype), run_pipe_datas))
            if tomo_input and ptype in ('rec'):
                # only allow the tomo_input result to be considered
                results = [tomo_input.pipe_data,]
                input_objects['tomo']=tomo_input
            if pick_input and ptype in ('pick'):
                # add pick as an input object
                results.append(pick_input.pipe_data)
                input_objects['pick']=pick_input
            for r in results:
                    # create instance of each relavent output and accumulate
                    # them for the next tomogram_path_type_order to provide reference.
                    my_pipe_pk = r.pipe.pk
                    print('ptype', ptype, r, my_pipe_pk)
                    print('before', self.created_objects)
                    try:
                        saved = self._save_instance(r,input_pipe_pks, input_objects)
                        if my_pipe_pk not in self.created_objects.keys():
                            self.created_objects[my_pipe_pk]=[]
                        self.created_objects[my_pipe_pk].append((ptype,saved))
                        print(self.created_objects)
                    except Exception as e:
                        raise
                        print('ERROR: not able to save pipe_id=%d' % my_pipe_pk)
        return True

    def _add_other_objects(self, class_name, my_rpdata, input_pipe_pks):
        """ TODO: These need to be reworked into adding real values
        """
        my_pipe = my_rpdata.pipe
        my_plan_by_run = my_rpdata.run.proc_plan
        # validate
        results = PipeInPlan.objects.filter(plan=my_plan_by_run,pipe=my_pipe)
        if not results:
            raise ValueError('pipe %s not in plan %s' % (my_pipe, my_plan_by_run.name))
        if len(results) > 1:
            # pipe in the plan should be unique
            raise ValueError('%d copies of pipe %s in plan %s' % (len(results), my_pipe, my_plan_by_run.name))
        my_pipe_step = results[0].step
        my_pipe_pk = my_pipe.pk
        self.created_objects[my_pipe_pk].append(('msi',self.msi_session))
        if class_name == 'Tomograms':
            ### TODO Really determine voxel and pixel spacings###
            if my_pipe.software.name == 'aretomo3' and my_pipe_step == 1:
                voxels = TomogramVoxelSpacing.objects.filter(spacing=5.0)
                voxel = voxels[0]
            else:
                voxels = TomogramVoxelSpacing.objects.filter(spacing=10.0)
                voxel = voxels[0]
            self.created_objects[my_pipe_pk].append(('vox',voxel))
            ### TODO Define recon method in pipe
            recon_methods = ReconMethod.objects.all()
            if not recon_methods:
                # Create default recon method
                recon_method = ReconMethod.objects.create()
            else:
                recon_method = recon_methods[0]
            self.created_objects[my_pipe_pk].append(('recmethod',recon_method))
        if class_name == 'Annotation':
            meth_map = {'pick':'template matching','seg':'ml semantic segamentation'}
            dtype = my_rpdata.pathtype.static_path.data_type
            anno_methods = AnnotationMethod.objects.filter(name=meth_map[dtype])
            if not anno_methods:
                # Create default recon method
                anno_method = AnnotationMethod.objects.create(name=meth_map[dtype])
            else:
                anno_method = anno_methods[0]
            self.created_objects[my_pipe_pk].append(('pickmethod',anno_method))

    def is_recon_ctf_deconvolved(self, pipe):
        '''
        Determine if ctf deconvolution is done in this pipe.
        '''
        if pipe is None:
            return False
        task_names = list(map((lambda x: x.name),pipe.tasks_performed.all()))
        output_types = list(map((lambda x: x.static_path.data_type),pipe.output.all()))
        input_types = list(map((lambda x: x.data_type),pipe.input.all()))
        pipe_joints = self._get_pipe_joints(pipe)
        if 'ctf deconvolution' in task_names:
            return True
        if set(['rec','deno','evn','odd']).intersection(output_types):
            if 'aln' in input_types and 'ctf' not in input_types:
                # alignment is an input but not ctf
                return False
            parent_tomo_pipe = self._get_tomo_pipe(pipe_joints)
            if not parent_tomo_pipe:
                return False
            else:
                # determined by input_pipes
                return self.is_recon_ctf_deconvolved(parent_tomo_pipe)
        return False

    def _get_tomo_pipe(self, pipe_joints):
        tomogram_making_data_type = ['tangl','rawst','aln','ctf','rec','evn','odd','deno']
        if pipe_joints:
            parent_tomo_pipe = None
            for pr in pipe_joints:
                if pr.input_pathtype.static_path.data_type in tomogram_making_data_type:
                    parent_tomo_pipe = pr.input_pipe_in_plan.pipe
                    return parent_tomo_pipe
        return None 
    
    def _save_instance(self, pdata, input_pipe_pks, input_objects={}):
        """
        Save instances of various cryo-ET models
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
                        'pickmethod':('AnnotationMethod','annotation_method'),
                        'pick':('Annotation','pick'),
                        'seg':('Annotation','segmentation'),
                        'galr':('ParticleGallery','gallery'),
                    }
        all_input_pipe_pks = list(input_pipe_pks)
        #
        # get my_instance from class in this python module
        ptype = pdata.pathtype.static_path.data_type
        class_name = model_map[ptype][0]
        my_attr = getattr_from_globals(class_name)
        my_instance = my_attr(pipe_data=pdata)
        #
        my_field_names = list(map((lambda x:x.name),my_instance._meta.fields))
        my_pipe = pdata.pipe
        my_pipe_pk = my_pipe.pk
        if my_pipe_pk not in self.created_objects.keys():
            # initiate created_object
            all_input_pipe_pks.append(my_pipe_pk)
            self.created_objects[my_pipe_pk]=[]
        created_in_my_pipe = self.created_objects[my_pipe_pk]
        pytype_created_in_my_pipe = list(map((lambda x:x[0]),created_in_my_pipe))
        if ptype in pytype_created_in_my_pipe:
            # no need to save instance
            return self.created_objects[my_pipe_pk][pytype_created_in_my_pipe.index(ptype)][1]
        # add the required objects that is not the main data pipeline
        self._add_other_objects(class_name, pdata, input_pipe_pks)


        # Use the index of the input_pipe to find the item to map the model fields to
        pipe_range = self._get_pipe_range(all_input_pipe_pks, my_pipe, input_objects)
        print('pipe_range', pipe_range)
        print('my_instance', my_instance)
        for i in pipe_range:
            pk = all_input_pipe_pks[i]
            for item in self.created_objects[pk]:
                k, obj = item
                attr_name = model_map[k][1]
                print('item', k, obj)
                print('checking against', my_field_names)
                # map the model fields to the previously created objects
                if attr_name in my_field_names:
                    if attr_name=='ctf':
                        # Without ctf input means the output tomogram is not ctf deconvoluted..
                        if not self.is_recon_ctf_deconvolved(my_pipe):
                            continue
                    setattr(my_instance, attr_name, obj)
                # denoised tomogram is derived from a parent
                if ptype == 'deno' and k == 'rec':
                    # tomogram is derived from others
                    setattr(my_instance,'parent_tomo', obj)
                    for attr_name in my_field_names:
                        if attr_name in ('id','pipe_data','parent_tomo'):
                            continue
                        setattr(my_instance, attr_name, getattr(obj, attr_name))
                # when tomograms are the input, it is referred as tomograms in model fields.
                if 'tomo_input' in input_objects.keys() and attr_name == 'tomograms':
                    setattr(my_instance,'tomograms', obj)

        # add everything created in my_pipe
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
        # specific to annotation
        atype_map = {'pick':'point','seg':'volume mask'}
        if ptype in ['pick','seg']:
            my_instance.name = my_pipe.name
            my_instance.annotation_type = atype_map[ptype]
        my_instance.save()
        return my_instance

    def _get_pipe_range(self, all_input_pipe_pks, my_pipe, input_objects):
        if input_objects:
            starts = []
            ends = []
            for k in input_objects.keys():
                input_obj = input_objects[k]
                my_input_pipe_pk = input_obj.pipe_data.pipe.pk
                starts.append(all_input_pipe_pks.index(input_obj.pipe_data.pipe.pk))
                ends.append(all_input_pipe_pks.index(my_input_pipe_pk)+1)
            start = min(starts)
            end = max(ends)
        else:
            my_pipe_joints = self._get_pipe_joints(my_pipe)
            if my_pipe_joints:
                my_input_pipe = self._get_tomo_pipe(my_pipe_joints)
                print('ptype input_pipe in all', my_input_pipe, all_input_pipe_pks)
                if not my_input_pipe:
                    end = 1
                else:
                    end = all_input_pipe_pks.index(my_input_pipe.pk)+1
            else:
                end = 1
            start = 0
        return range(start,end)

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
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query

class Frames(models.Model):
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE, related_name='session_of_frames') # included here for easy query
    frame_path = models.ForeignKey(Path, related_name='processing_frame_path',on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.frame_path)

class RawTiltSeries(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query
    angles = models.ForeignKey(TiltAngles, on_delete=models.CASCADE)
    frames = models.ForeignKey(Frames, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

class Ctf(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query
    tiltseries = models.ForeignKey(RawTiltSeries, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

class Alignment(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query
    tiltseries = models.ForeignKey(RawTiltSeries, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

class TomogramVoxelSpacing(models.Model):
    spacing = models.FloatField(default=10.0, help_text='uniform voxel spacing in angstroms')

    def __str__(self):
        return '%.3f' % (self.spacing)

class ReconMethod(models.Model):
    """
    Processing Method that creates tomogram from alignment
    """
    name = models.CharField(max_length=32, default='weighted back projection')

    def __str__(self):
        return '%s' % (self.name)

class TomoPostProcessMethod(models.Model):
    """
    Processing Method that converts one tomogram into another through filtering, denoising etc.
    """
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

    def __str__(self):
        return 'tomo @ %s' % (self.pipe_data)

class AnnotationMethod(models.Model):
    name = models.CharField(max_length=32, default='template matching')

    def __str__(self):
        return '%s' % (self.name)

class Annotation(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query
    tomograms = models.ForeignKey(Tomograms, on_delete=models.CASCADE)
    name = models.CharField(max_length=32, default='ribosome')
    ontology_term = models.CharField(max_length=20, default='GO:0005840')
    annotation_type = models.CharField(max_length=12, default='point')
    annotation_method = models.ForeignKey(AnnotationMethod, on_delete=models.CASCADE)
    parent_anno = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    notes = models.TextField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s' % (self.pipe_data)

class ParticleGallery(models.Model):
    pipe_data = models.ForeignKey(RunPipeData, on_delete=models.CASCADE)
    msi_session = models.ForeignKey(MsiSession, on_delete=models.CASCADE) # included here for easy query
    tomograms = models.ForeignKey(Tomograms, on_delete=models.CASCADE)
    pick = models.ForeignKey(Annotation, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % (self.pipe_data)

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


def select_plan_ids_by_input_data_types(selected_data_types):
    selected_static_paths = StaticPath.objects.filter(data_type__in=selected_data_types)
    selected_pipes = Pipe.objects.filter(input__in=selected_static_paths)
    pipe_in_plans = PipeInPlan.objects.filter(pipe__in=selected_pipes)
    plan_ids = list(map((lambda x: x.plan.id), pipe_in_plans))
    return plan_ids




class JobLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_name = models.CharField(max_length=150, null=True, blank=True)
    advanced = models.BooleanField(default=False)
    job_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(default=now)

    # <-- Add a JSONField to store all job parameters
    parameters = models.JSONField(null=True, blank=True)

    # Optionally store any error messages
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Aretomo Job {self.job_id} by {self.user.username}"

class Review(models.Model):
    """
    A review record for an MSI session, containing review metadata and status.
    """
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review_name = models.CharField(max_length=255)
    review_type = models.CharField(max_length=100)
    run_id = models.CharField(max_length=100)
    reconstruction_type = models.CharField(max_length=100)
    total_count = models.IntegerField(default=0)
    reviewed_count = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default='pending')  # pending, in_progress, completed, rejected
    save_path = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.ForeignKey(MsiSession, on_delete=models.CASCADE, related_name='reviews')
    requestor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='requested_reviews')

    def __str__(self):
        return f'Review {self.review_name} for {self.session.name}'

class ReviewTomogram(models.Model):
    """
    A tomogram review record, linking specific tomograms to a review.
    """
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='review_tomograms')
    tomogram_id = models.CharField(max_length=100, primary_key=True)
    position_id = models.CharField(max_length=100)
    quality = models.CharField(
        max_length=20,
        choices=[
            ('', ''),
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
            ('uncertain', 'Uncertain')
        ],
        default=''
    )
    rejection_reasons = models.JSONField(default=list, blank=True)  # Array of strings
    object_labels = models.JSONField(default=list, blank=True)  # Array of objects
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['review', 'tomogram_id']

    def __str__(self):
        return f'Tomogram Review {self.tomogram_id} in {self.review}'