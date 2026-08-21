from django.contrib import admin

from .models import Cluster, DataKind, Path, PathType

# Register your models here.
admin.site.register(Path)
admin.site.register(PathType)
admin.site.register(DataKind)


@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("cluster_id", "name", "http_base_url", "ssh_hostname", "ssh_port", "is_active", "is_default")
    list_editable = ("is_active", "is_default")
    list_filter = ("is_active", "is_default")
    search_fields = ("cluster_id", "name", "ssh_hostname")
