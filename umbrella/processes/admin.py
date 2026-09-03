from django.contrib import admin
from django.db.models import Count

from .models import (
    Alignment,
    Annotation,
    AnnotationMethod,
    Ctf,
    DirectorySummary,
    FilesystemSurvey,
    Frames,
    ParticleGallery,
    Pipe,
    PipeExecution,
    PipeInPlan,
    PipeJoint,
    ProcPlan,
    ProcRun,
    ProcSoftware,
    RawTiltSeries,
    ReconMethod,
    Review,
    ReviewTomogram,
    RunPipeData,
    Task,
    TiltAngles,
    Tomograms,
    TomogramVoxelSpacing,
    TomoPostProcessMethod,
)

# Register your models here.
admin.site.register(Task)


@admin.register(ProcSoftware)
class ProcSoftwareAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "version",
        "processor_class",
        "default_cluster",
        "storage_dirname",
    )
    list_editable = ("storage_dirname",)
    autocomplete_fields = ("processing_root", "script_dir", "output_patterns")
    list_filter = ("default_cluster",)
    search_fields = ("name", "processor_class")
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("name", "version", "capable_tasks"),
            },
        ),
        (
            "Execution Configuration",
            {
                "fields": (
                    "processor_class",
                    "default_cluster",
                    "allowed_clusters",
                    "processing_root",
                    "script_dir",
                    "output_patterns",
                ),
                "description": (
                    "Configure how this software runs on clusters. Leave the two directory "
                    "templates blank to use the shared processing_root / script_dir "
                    "templates (Stores → Path types); set them only for a software whose "
                    "directories don't follow the standard layout. Output patterns name this "
                    "software's output files; a session plan's tilt_series binding of the "
                    "same data kind overrides them per plan."
                ),
            },
        ),
        (
            "Storage",
            {
                "fields": ("storage_dirname",),
                "description": (
                    "Which directory on the cluster this software writes into, used to group the Storage Explorer. "
                ),
            },
        ),
        (
            "Legacy",
            {
                "fields": ("callback_function", "logger"),
                "classes": ("collapse",),
                "description": "Deprecated fields from old execution system",
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add help text for allowed_clusters in the form
        if "allowed_clusters" in form.base_fields:
            form.base_fields[
                "allowed_clusters"
            ].help_text = (
                'Enter a JSON list of cluster IDs, e.g., ["czii", "bruno"]. Leave empty to allow all clusters.'
            )
        return form


@admin.register(ProcPlan)
class ProcPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "software_names", "run_count")
    list_editable = ("display_name",)
    search_fields = ("name", "display_name")
    ordering = ("name",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("pipeinplan_set__pipe__software")
            .annotate(_run_count=Count("procrun", distinct=True))
        )

    @admin.display(description="Software (from pipes)")
    def software_names(self, obj):
        names = {pip.pipe.software.name for pip in obj.pipeinplan_set.all()}
        return ", ".join(sorted(names)) or "—"

    @admin.display(description="Runs", ordering="_run_count")
    def run_count(self, obj):
        return obj._run_count


admin.site.register(Pipe)
admin.site.register(PipeJoint)
admin.site.register(PipeInPlan)
admin.site.register(ProcRun)
admin.site.register(RunPipeData)


@admin.register(PipeExecution)
class PipeExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "job_id",
        "status",
        "syncer_active",
        "proc_run",
        "pipe_in_plan",
        "submitted_at",
        "started_at",
        "completed_at",
    )
    list_filter = ("status", "syncer_active")
    search_fields = ("job_id", "proc_run__name")
    readonly_fields = ("submitted_at", "started_at", "completed_at", "created_at", "updated_at")
    ordering = ("-submitted_at",)


admin.site.register(Frames)
admin.site.register(RawTiltSeries)
admin.site.register(TiltAngles)
admin.site.register(Ctf)
admin.site.register(Alignment)
admin.site.register(ReconMethod)
admin.site.register(TomogramVoxelSpacing)
admin.site.register(Tomograms)
admin.site.register(TomoPostProcessMethod)
admin.site.register(AnnotationMethod)
admin.site.register(Annotation)
admin.site.register(ParticleGallery)
admin.site.register(Review)
admin.site.register(ReviewTomogram)


@admin.register(FilesystemSurvey)
class FilesystemSurveyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cluster",
        "status",
        "base_path",
        "job_id",
        "total_files",
        "get_size_display",
        "submitted_at",
        "completed_at",
    )
    list_filter = ("cluster", "status")
    search_fields = ("base_path", "job_id")
    readonly_fields = (
        "submitted_at",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
        "total_files",
        "total_directories",
        "total_size_bytes",
    )
    ordering = ("-created_at",)
    fieldsets = (
        (
            "Survey Info",
            {
                "fields": ("cluster", "base_path", "status", "submitted_by"),
            },
        ),
        (
            "SLURM Job",
            {
                "fields": ("job_id", "results_parquet_path"),
            },
        ),
        (
            "Statistics",
            {
                "fields": ("total_files", "total_directories", "total_size_bytes", "size_by_user", "count_by_user"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("submitted_at", "started_at", "completed_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Errors",
            {
                "fields": ("error_message",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(DirectorySummary)
class DirectorySummaryAdmin(admin.ModelAdmin):
    list_display = (
        "path",
        "cluster",
        "origin",
        "file_count",
        "get_size_display",
        "preserve_status",
        "owner_username",
        "depth",
    )
    list_filter = ("cluster", "origin", "preserve_status", "survey")
    search_fields = ("path", "owner_username")
    readonly_fields = ("created_at", "updated_at", "newest_file_mtime", "oldest_file_mtime")
    ordering = ("path",)
    raw_id_fields = ("survey", "status_updated_by")
    list_per_page = 50
