from django.contrib import admin

from .models import (
    Dataset,
    DatasetFunding,
    DatasetJob,
    Deposition,
    DepositionAnnotation,
    DepositionAnnotationMethodLink,
    DepositionSession,
    TiltseriesMetadata,
    TomogramMetadata,
)


class DatasetInline(admin.TabularInline):
    model = Dataset
    extra = 0
    fields = ("dataset_id", "title", "status")
    show_change_link = True


@admin.register(Deposition)
class DepositionAdmin(admin.ModelAdmin):
    list_display = ("deposition_id", "title", "submitter_user", "release_date", "created_at")
    search_fields = ("title", "deposition_id", "description")
    raw_id_fields = ("submitter_user",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [DatasetInline]


class DatasetFundingInline(admin.TabularInline):
    model = DatasetFunding
    extra = 0


class DepositionSessionInline(admin.TabularInline):
    model = DepositionSession
    extra = 0
    fields = ("msi_session", "aretomo_run_name", "denoise_run_name")
    raw_id_fields = ("msi_session",)
    show_change_link = True


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("dataset_id", "title", "deposition", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "dataset_id", "description")
    raw_id_fields = ("deposition", "sample")
    readonly_fields = ("created_at", "updated_at")
    inlines = [DatasetFundingInline, DepositionSessionInline]


@admin.register(DatasetJob)
class DatasetJobAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "state", "prep_slurm_job_id", "push_slurm_job_id", "updated_at")
    list_filter = ("state",)
    raw_id_fields = ("dataset",)
    readonly_fields = ("created_at", "updated_at")


class TiltseriesMetadataInline(admin.StackedInline):
    model = TiltseriesMetadata
    extra = 0
    max_num = 1


class TomogramMetadataInline(admin.StackedInline):
    model = TomogramMetadata
    extra = 0
    max_num = 1


class DepositionAnnotationInline(admin.TabularInline):
    model = DepositionAnnotation
    extra = 0
    fields = ("copick_kind", "copick_ref", "object_name", "is_selected")
    show_change_link = True


@admin.register(DepositionSession)
class DepositionSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "dataset", "msi_session", "aretomo_run_name", "denoise_run_name")
    search_fields = ("aretomo_run_name", "denoise_run_name")
    raw_id_fields = ("dataset", "msi_session")
    readonly_fields = ("created_at", "updated_at", "last_autofill_at", "last_autofill_duration_seconds")
    inlines = [TiltseriesMetadataInline, TomogramMetadataInline, DepositionAnnotationInline]


class MethodLinkInline(admin.TabularInline):
    model = DepositionAnnotationMethodLink
    extra = 0


@admin.register(DepositionAnnotation)
class DepositionAnnotationAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "copick_kind", "object_name", "is_selected", "is_visualization_default")
    list_filter = ("copick_kind", "method_type", "is_selected")
    search_fields = ("object_name", "copick_ref", "object_id")
    raw_id_fields = ("session",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [MethodLinkInline]
