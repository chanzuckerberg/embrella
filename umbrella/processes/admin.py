from django.contrib import admin

from .models import (
    Alignment,
    Annotation,
    AnnotationMethod,
    Ctf,
    DirectorySummary,
    FilesystemSurvey,
    Frames,
    GlobalParam,
    MetaKey,
    ParticleGallery,
    Pipe,
    PipeExecution,
    PipeInPlan,
    PipeJoint,
    PipeParam,
    ProcPlan,
    ProcRun,
    ProcSoftware,
    RawTiltSeries,
    ReconMethod,
    Review,
    ReviewTomogram,
    RunGlobalValue,
    RunPipeData,
    RunPipeValue,
    Task,
    TiltAngles,
    Tomograms,
    TomogramVoxelSpacing,
    TomoPostProcessMethod,
)

# Register your models here.
admin.site.register(MetaKey)
admin.site.register(Task)


@admin.register(ProcSoftware)
class ProcSoftwareAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'processor_class', 'default_cluster', 'script_directory')
    list_filter = ('default_cluster',)
    search_fields = ('name', 'processor_class')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'version', 'capable_tasks'),
        }),
        ('Execution Configuration', {
            'fields': ('processor_class', 'default_cluster', 'allowed_clusters', 'script_directory'),
            'description': 'Configure how this software runs on clusters',
        }),
        ('Legacy', {
            'fields': ('callback_function', 'logger'),
            'classes': ('collapse',),
            'description': 'Deprecated fields from old execution system',
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add help text for allowed_clusters in the form
        if 'allowed_clusters' in form.base_fields:
            form.base_fields['allowed_clusters'].help_text = (
                'Enter a JSON list of cluster IDs, e.g., ["czii", "bruno"]. '
                'Leave empty to allow all clusters.'
            )
        return form


admin.site.register(ProcPlan)
admin.site.register(Pipe)
admin.site.register(PipeJoint)
admin.site.register(PipeInPlan)
admin.site.register(GlobalParam)
admin.site.register(PipeParam)
admin.site.register(ProcRun)
admin.site.register(RunGlobalValue)
admin.site.register(RunPipeValue)
admin.site.register(RunPipeData)


@admin.register(PipeExecution)
class PipeExecutionAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'status', 'syncer_active', 'proc_run', 'pipe_in_plan', 'submitted_at', 'started_at', 'completed_at')
    list_filter = ('status', 'syncer_active')
    search_fields = ('job_id', 'proc_run__name')
    readonly_fields = ('submitted_at', 'started_at', 'completed_at', 'created_at', 'updated_at')
    ordering = ('-submitted_at',)


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
    list_display = ('id', 'cluster', 'status', 'base_path', 'job_id', 'total_files', 'get_size_display', 'submitted_at', 'completed_at')
    list_filter = ('cluster', 'status')
    search_fields = ('base_path', 'job_id')
    readonly_fields = ('submitted_at', 'started_at', 'completed_at', 'created_at', 'updated_at', 'total_files', 'total_directories', 'total_size_bytes')
    ordering = ('-created_at',)
    fieldsets = (
        ('Survey Info', {
            'fields': ('cluster', 'base_path', 'status', 'submitted_by'),
        }),
        ('SLURM Job', {
            'fields': ('job_id', 'results_parquet_path'),
        }),
        ('Statistics', {
            'fields': ('total_files', 'total_directories', 'total_size_bytes', 'size_by_user', 'count_by_user'),
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'started_at', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
        ('Errors', {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
    )


@admin.register(DirectorySummary)
class DirectorySummaryAdmin(admin.ModelAdmin):
    list_display = ('path', 'cluster', 'origin', 'file_count', 'get_size_display', 'preserve_status', 'owner_username', 'depth')
    list_filter = ('cluster', 'origin', 'preserve_status', 'survey')
    search_fields = ('path', 'owner_username')
    readonly_fields = ('created_at', 'updated_at', 'newest_file_mtime', 'oldest_file_mtime')
    ordering = ('path',)
    raw_id_fields = ('survey', 'status_updated_by')
    list_per_page = 50
