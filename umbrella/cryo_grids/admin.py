import logging

from django.contrib import admin
from django.http import HttpResponseRedirect

from .models import (
    Cane,
    CryoGrid,
    CryoGridBox,
    CryoGridCassette,
    Dewar,
    GridLabel,
    Label,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Sample,
    Site,
    Specimen,
)

logger = logging.getLogger(__name__)


def build_frontend_url_with_state(request, base_path="/samples/grid_logging"):
    """Build a same-origin frontend URL with state parameters from request"""
    frontend_url = base_path

    # Get state parameters from request
    state_params = []

    # User ID state
    return_user_id = request.GET.get("return_user_id")
    if return_user_id:
        state_params.append(f"user_id={return_user_id}")

    # Puck ID state
    return_puck_id = request.GET.get("return_puck_id")
    if return_puck_id:
        state_params.append(f"puck_id={return_puck_id}")

    # Slot position state
    return_slot_position = request.GET.get("return_slot_position")
    if return_slot_position:
        state_params.append(f"slot_position={return_slot_position}")

    # Grid position state
    return_grid_position = request.GET.get("return_grid_position")
    if return_grid_position:
        state_params.append(f"grid_position={return_grid_position}")

    # Grid ID state
    return_grid_id = request.GET.get("return_grid_id")
    if return_grid_id:
        state_params.append(f"grid_id={return_grid_id}")

    # Add state parameters to URL if any exist
    if state_params:
        frontend_url += "?" + "&".join(state_params)
    return frontend_url


# Register standard models
admin.site.register(Site)
admin.site.register(Dewar)
admin.site.register(Cane)
admin.site.register(CryoGridCassette)
admin.site.register(PlungeFreezingDevice)
admin.site.register(PlungeFreezingSession)
admin.site.register(Sample)
admin.site.register(Specimen)
admin.site.register(Label)
admin.site.register(GridLabel)


# Custom admin classes for models that need redirect
class PuckAdmin(admin.ModelAdmin):
    # def response_add(self, request, obj, post_url_continue=None):
    #     if "_addanother" not in request.POST and "_continue" not in request.POST:
    #         frontend_url = build_frontend_url_with_state(request)
    #         return HttpResponseRedirect(frontend_url)

    # def response_change(self, request, obj):
    #     if "_addanother" not in request.POST and "_continue" not in request.POST:
    #         frontend_url = build_frontend_url_with_state(request)
    #         return HttpResponseRedirect(frontend_url)

    def response_delete(self, request, obj_display, obj_id):
        frontend_url = build_frontend_url_with_state(request)
        return HttpResponseRedirect(frontend_url)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


class CryoGridBoxAdmin(admin.ModelAdmin):
    # def response_add(self, request, obj, post_url_continue=None):
    #     if "_addanother" not in request.POST and "_continue" not in request.POST:
    #         frontend_url = build_frontend_url_with_state(request)
    #         return HttpResponseRedirect(frontend_url)

    # def response_change(self, request, obj):
    #     if "_addanother" not in request.POST and "_continue" not in request.POST:
    #         frontend_url = build_frontend_url_with_state(request)
    #         return HttpResponseRedirect(frontend_url)

    def response_delete(self, request, obj_display, obj_id):
        frontend_url = build_frontend_url_with_state(request)
        return HttpResponseRedirect(frontend_url)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


class CryoGridAdmin(admin.ModelAdmin):
    # def response_add(self, request, obj, post_url_continue=None):
    #     if "_addanother" not in request.POST and "_continue" not in request.POST:
    #         frontend_url = build_frontend_url_with_state(request)
    #         return HttpResponseRedirect(frontend_url)

    # def response_change(self, request, obj):
    #     if "_addanother" not in request.POST and "_continue" not in request.POST:
    #         frontend_url = build_frontend_url_with_state(request)
    #         return HttpResponseRedirect(frontend_url)

    def response_delete(self, request, obj_display, obj_id):
        frontend_url = build_frontend_url_with_state(request)
        return HttpResponseRedirect(frontend_url)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                "show_save_and_add_another": False,
                "show_save_and_continue": False,
            }
        )
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


# Register models with custom admin classes
admin.site.register(CryoGrid, CryoGridAdmin)
admin.site.register(Puck, PuckAdmin)
admin.site.register(CryoGridBox, CryoGridBoxAdmin)
