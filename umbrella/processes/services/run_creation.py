"""
Run creation service for managing ProcRun tomogram collection setup.

This service encapsulates complex business logic for creating tomogram collections
and managing processing run data, extracted from the ProcRun model.
"""

from processes.models import (
    AnnotationMethod,
    Frames,
    PipeInPlan,
    PipeJoint,
    ReconMethod,
    RunPipeData,
    TomogramVoxelSpacing,
    TomoPostProcessMethod,
    getattr_from_globals,
)


class RunCreationService:
    """
    Service for managing processing run creation and tomogram collection setup.

    Extracted from ProcRun model to separate business logic from data model.
    """

    @staticmethod
    def create_frames_runpipedata(proc_run, msi_session):
        """
        Frames are input of the first processing. This method creates its record.

        Args:
            proc_run: ProcRun instance
            msi_session: MsiSession instance

        Returns:
            Frames instance
        """
        # frames are done in a different mechanism from others
        s = proc_run.msi_session
        frames_fd = Frames.objects.create(
            session_plan=s.session_plan,
            msi_session=s,
            frame_path=s.frames,
        )
        frames_fd.save()
        return frames_fd

    @staticmethod
    def get_pipe_joints(pipe):
        """Get all pipe joints for a given pipe."""
        joints = PipeJoint.objects.filter(pipe_in_plan__pipe=pipe)
        return joints

    @staticmethod
    def get_input_pipe_pks(proc_run, pipe):
        """Get primary keys of input pipes for a given pipe."""
        joints = RunCreationService.get_pipe_joints(pipe)
        input_pipes = list(set(map((lambda x: x.input_pipe_in_plan.pipe), joints)))
        print(input_pipes)
        pks = list(set(map((lambda x: x.pk), input_pipes)))
        if not pks:
            return [0]  # from msi_session acquisition
        return pks

    @staticmethod
    def add_other_objects(proc_run, class_name, my_rpdata, input_pipe_pks):
        """
        Add metadata objects (voxel spacing, recon methods, annotation methods).

        TODO: These need to be reworked into adding real values

        Args:
            proc_run: ProcRun instance with created_objects dict
            class_name: Name of the model class being created
            my_rpdata: RunPipeData instance
            input_pipe_pks: List of input pipe PKs
        """
        my_pipe = my_rpdata.pipe
        my_plan_by_run = my_rpdata.run.proc_plan
        # validate
        results = PipeInPlan.objects.filter(plan=my_plan_by_run, pipe=my_pipe)
        if not results:
            raise ValueError("pipe %s not in plan %s" % (my_pipe, my_plan_by_run.name))
        if len(results) > 1:
            # pipe in the plan should be unique
            raise ValueError("%d copies of pipe %s in plan %s" % (len(results), my_pipe, my_plan_by_run.name))
        my_pipe_step = results[0].step
        my_pipe_pk = my_pipe.pk
        proc_run.created_objects[my_pipe_pk].append(("msi", proc_run.msi_session))
        if class_name == "Tomograms":
            ### TODO Really determine voxel and pixel spacings###
            if my_pipe.software.name == "aretomo3" and my_pipe_step == 1:
                voxels = TomogramVoxelSpacing.objects.filter(spacing=5.0)
                voxel = voxels[0]
            else:
                voxels = TomogramVoxelSpacing.objects.filter(spacing=10.0)
                voxel = voxels[0]
            proc_run.created_objects[my_pipe_pk].append(("vox", voxel))
            ### TODO Define recon method in pipe
            recon_methods = ReconMethod.objects.all()
            if not recon_methods:
                # Create default recon method
                recon_method = ReconMethod.objects.create()
            else:
                recon_method = recon_methods[0]
            proc_run.created_objects[my_pipe_pk].append(("recmethod", recon_method))
        if class_name == "Annotation":
            meth_map = {"pick": "template matching", "seg": "ml semantic segamentation"}
            dtype = my_rpdata.pathtype.data_kind.data_type
            anno_methods = AnnotationMethod.objects.filter(name=meth_map[dtype])
            if not anno_methods:
                # Create default recon method
                anno_method = AnnotationMethod.objects.create(name=meth_map[dtype])
            else:
                anno_method = anno_methods[0]
            proc_run.created_objects[my_pipe_pk].append(("pickmethod", anno_method))

    @staticmethod
    def is_recon_ctf_deconvolved(proc_run, pipe):
        """
        Determine if ctf deconvolution is done in this pipe.

        Args:
            proc_run: ProcRun instance
            pipe: Pipe instance

        Returns:
            bool: True if CTF deconvolution is done
        """
        if pipe is None:
            return False
        task_names = list(map((lambda x: x.name), pipe.tasks_performed.all()))
        output_types = list(map((lambda x: x.data_kind.data_type), pipe.output.all()))
        input_types = list(map((lambda x: x.data_type), pipe.input.all()))
        pipe_joints = RunCreationService.get_pipe_joints(pipe)
        if "ctf deconvolution" in task_names:
            return True
        if set(["rec", "deno", "evn", "odd"]).intersection(output_types):
            if "aln" in input_types and "ctf" not in input_types:
                # alignment is an input but not ctf
                return False
            parent_tomo_pipe = RunCreationService.get_tomo_pipe(pipe_joints)
            if not parent_tomo_pipe:
                return False
            else:
                # determined by input_pipes
                return RunCreationService.is_recon_ctf_deconvolved(proc_run, parent_tomo_pipe)
        return False

    @staticmethod
    def get_tomo_pipe(pipe_joints):
        """Get parent tomogram pipe from pipe joints."""
        tomogram_making_data_type = ["tangl", "rawst", "aln", "ctf", "rec", "evn", "odd", "deno"]
        if pipe_joints:
            parent_tomo_pipe = None
            for pr in pipe_joints:
                if pr.input_pathtype.data_kind.data_type in tomogram_making_data_type:
                    parent_tomo_pipe = pr.input_pipe_in_plan.pipe
                    return parent_tomo_pipe
        return None

    @staticmethod
    def get_pipe_range(proc_run, all_input_pipe_pks, my_pipe, input_objects):
        """
        Determine range of input objects for a given pipe.

        Args:
            proc_run: ProcRun instance
            all_input_pipe_pks: List of all input pipe PKs
            my_pipe: Current pipe
            input_objects: Dictionary of input objects

        Returns:
            range: Range of indices to process
        """
        if input_objects:
            starts = []
            ends = []
            for k in input_objects.keys():
                input_obj = input_objects[k]
                my_input_pipe_pk = input_obj.pipe_data.pipe.pk
                starts.append(all_input_pipe_pks.index(input_obj.pipe_data.pipe.pk))
                ends.append(all_input_pipe_pks.index(my_input_pipe_pk) + 1)
            start = min(starts)
            end = max(ends)
        else:
            my_pipe_joints = RunCreationService.get_pipe_joints(my_pipe)
            if my_pipe_joints:
                my_input_pipe = RunCreationService.get_tomo_pipe(my_pipe_joints)
                print("ptype input_pipe in all", my_input_pipe, all_input_pipe_pks)
                if not my_input_pipe:
                    end = 1
                else:
                    end = all_input_pipe_pks.index(my_input_pipe.pk) + 1
            else:
                end = 1
            start = 0
        return range(start, end)

    @staticmethod
    def save_instance(proc_run, pdata, input_pipe_pks, input_objects=None):
        """
        Save instances of various cryo-ET models.

        Args:
            proc_run: ProcRun instance with created_objects dict
            pdata: RunPipeData instance
            input_pipe_pks: List of input pipe PKs
            input_objects: Optional dict of input objects

        Returns:
            Saved model instance
        """
        if input_objects is None:
            input_objects = {}

        model_map = {
            # PathType.static_name: (class name, attribute name in other classes)
            "frames": ("Frames", "frames"),
            "rawst": ("RawTiltSeries", "tiltseries"),
            "tangl": ("TiltAngles", "angles"),
            "aln": ("Alignment", "alignment"),
            "ctf": ("Ctf", "ctf"),
            "recmethod": ("ReconMethod", "recon_method"),
            "vox": ("TomogramVoxelSpacing", "voxel_spacing"),
            "rec": ("Tomograms", "tomograms"),
            "deno": ("Tomograms", "tomograms"),
            "msi": ("MsiSession", "msi_session"),
            "pickmethod": ("AnnotationMethod", "annotation_method"),
            "pick": ("Annotation", "pick"),
            "seg": ("Annotation", "segmentation"),
            "galr": ("ParticleGallery", "gallery"),
        }
        all_input_pipe_pks = list(input_pipe_pks)
        #
        # get my_instance from class in this python module
        ptype = pdata.pathtype.data_kind.data_type
        class_name = model_map[ptype][0]
        my_attr = getattr_from_globals(class_name)
        my_instance = my_attr(pipe_data=pdata)
        #
        my_field_names = list(map((lambda x: x.name), my_instance._meta.fields))
        my_pipe = pdata.pipe
        my_pipe_pk = my_pipe.pk
        if my_pipe_pk not in proc_run.created_objects.keys():
            # initiate created_object
            all_input_pipe_pks.append(my_pipe_pk)
            proc_run.created_objects[my_pipe_pk] = []
        created_in_my_pipe = proc_run.created_objects[my_pipe_pk]
        pytype_created_in_my_pipe = list(map((lambda x: x[0]), created_in_my_pipe))
        if ptype in pytype_created_in_my_pipe:
            # no need to save instance
            return proc_run.created_objects[my_pipe_pk][pytype_created_in_my_pipe.index(ptype)][1]
        # add the required objects that is not the main data pipeline
        RunCreationService.add_other_objects(proc_run, class_name, pdata, input_pipe_pks)

        # Use the index of the input_pipe to find the item to map the model fields to
        pipe_range = RunCreationService.get_pipe_range(proc_run, all_input_pipe_pks, my_pipe, input_objects)
        print("pipe_range", pipe_range)
        print("my_instance", my_instance)
        for i in pipe_range:
            pk = all_input_pipe_pks[i]
            for item in proc_run.created_objects[pk]:
                k, obj = item
                attr_name = model_map[k][1]
                print("item", k, obj)
                print("checking against", my_field_names)
                # map the model fields to the previously created objects
                if attr_name in my_field_names:
                    if attr_name == "ctf":
                        # Without ctf input means the output tomogram is not ctf deconvoluted..
                        if not RunCreationService.is_recon_ctf_deconvolved(proc_run, my_pipe):
                            continue
                    setattr(my_instance, attr_name, obj)
                # denoised tomogram is derived from a parent
                if ptype == "deno" and k == "rec":
                    # tomogram is derived from others
                    my_instance.parent_tomo = obj
                    for attr_name in my_field_names:
                        if attr_name in ("id", "pipe_data", "parent_tomo"):
                            continue
                        setattr(my_instance, attr_name, getattr(obj, attr_name))
                # when tomograms are the input, it is referred as tomograms in model fields.
                if "tomo_input" in input_objects.keys() and attr_name == "tomograms":
                    my_instance.tomograms = obj

        # add everything created in my_pipe
        for item in proc_run.created_objects[my_pipe_pk]:
            k, obj = item
            if model_map[k][1] in my_field_names:
                setattr(my_instance, model_map[k][1], obj)
        # specific to denoised tomogram
        if ptype == "deno":
            deno_methods = TomoPostProcessMethod.objects.filter(software=pdata.pipe.software)
            if not deno_methods:
                # Create default method. TODO: should specify names
                deno_method = TomoPostProcessMethod.objects.create(software=pdata.pipe.software)
            else:
                deno_method = deno_methods[0]
            my_instance.post_process = deno_method
        # specific to annotation
        atype_map = {"pick": "point", "seg": "volume mask"}
        if ptype in ["pick", "seg"]:
            my_instance.name = my_pipe.name
            my_instance.annotation_type = atype_map[ptype]
        my_instance.save()
        return my_instance

    @staticmethod
    def create_tomogram_collection(proc_run, input_objects=None):
        """
        Save data-portal schema-like record. Return True if the run adds data to these records.

        Args:
            proc_run: ProcRun instance
            input_objects: Optional dict with 'tomo' and 'pick' keys

        Returns:
            bool: True if run adds data to records
        """
        if input_objects is None:
            input_objects = {}

        tomogram_path_type_order = ["tangl", "rawst", "aln", "ctf", "rec", "deno", "seg", "pick", "galr"]
        run_pipe_datas = RunPipeData.objects.filter(run=proc_run)
        pipes_input_from = []
        frames_fd = None
        for pipl in proc_run.pipes_in_plan:
            if not RunCreationService.get_pipe_joints(pipl.pipe):
                # handle frames
                # TODO: consider doing this at the time of msi_session creation
                frames_fd = RunCreationService.create_frames_runpipedata(proc_run, proc_run.msi_session)
            pipes_input_from.extend(RunCreationService.get_input_pipe_pks(proc_run, pipl.pipe))
        path_types = list(map((lambda x: x.pathtype.data_kind.data_type), run_pipe_datas))
        # TODO: this makes it necessary to enter pipes in strict order.
        input_pipe_pks = pipes_input_from
        print("all input pipe pks", input_pipe_pks)
        if input_objects:
            tomo_input = input_objects.get("tomo")
            pick_input = input_objects.get("pick")
        else:
            tomo_input = False
            pick_input = False
        if not tomo_input:
            if frames_fd:
                # processing run starts from frames
                proc_run.created_objects = {0: [("frames", frames_fd)]}  # by pipe pk
        else:
            # processing run starts from tomogram
            pipe_pk = tomo_input.pipe_data.pipe.pk
            ptype = tomo_input.pipe_data.pathtype.data_kind.data_type
            proc_run.created_objects = {pipe_pk: [(ptype, tomo_input)]}
            input_pipe_pks = [tomo_input.pipe_data.pipe.pk]
            if pick_input:
                # processing run needing pick_input such as 2d gallery making
                pipe_pk = pick_input.pipe_data.pipe.pk
                ptype = pick_input.pipe_data.pathtype.data_kind.data_type
                proc_run.created_objects[pipe_pk] = [(ptype, pick_input)]
                input_pipe_pks.append(pick_input.pipe_data.pipe.pk)

        input_objects = {}
        # accumulate created_objects
        for ptype in tomogram_path_type_order:
            results = list(filter((lambda x: x.pathtype.data_kind.data_type == ptype), run_pipe_datas))
            if tomo_input and ptype in ("rec"):
                # only allow the tomo_input result to be considered
                results = [tomo_input.pipe_data]
                input_objects["tomo"] = tomo_input
            if pick_input and ptype in ("pick"):
                # add pick as an input object
                results.append(pick_input.pipe_data)
                input_objects["pick"] = pick_input
            for r in results:
                # create instance of each relavent output and accumulate
                # them for the next tomogram_path_type_order to provide reference.
                my_pipe_pk = r.pipe.pk
                print("ptype", ptype, r, my_pipe_pk)
                print("before", proc_run.created_objects)
                try:
                    saved = RunCreationService.save_instance(proc_run, r, input_pipe_pks, input_objects)
                    if my_pipe_pk not in proc_run.created_objects.keys():
                        proc_run.created_objects[my_pipe_pk] = []
                    proc_run.created_objects[my_pipe_pk].append((ptype, saved))
                    print(proc_run.created_objects)
                except Exception:
                    print("ERROR: not able to save pipe_id=%d" % my_pipe_pk)
                    raise
        return True
