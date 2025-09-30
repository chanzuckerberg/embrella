from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django import forms
import datetime
import logging
import os

from .models import Site, Dewar, Cane, Puck, CryoGridBox, CryoGridCassette
from .models import PlungeFreezingDevice, PlungeFreezingSession, Specimen, CryoGrid, Sample
from .views import _save_copied_grid, get_available_positions

logger = logging.getLogger(__name__)

# Add this function to get the correct frontend URL
def get_frontend_url():
    """Get the frontend URL based on environment"""
    environment = os.getenv('DJANGO_ENV', 'development')
    if environment == 'staging':
        return 'http://umbrella-dev.czbiohub.org/next'
    elif environment == 'production':
        return 'http://umbrella.czbiohub.org/next'
    else:  # development
        return 'http://localhost:3000/next'
    
def build_frontend_url_with_state(request, base_path="/grid_logging"):
    """Build frontend URL with state parameters from request"""
    frontend_url = f"{get_frontend_url()}{base_path}"
    
    # Get state parameters from request
    state_params = []
    
    # User ID state
    return_user_id = request.GET.get('return_user_id')
    if return_user_id:
        state_params.append(f"user_id={return_user_id}")
    
    # Puck ID state  
    return_puck_id = request.GET.get('return_puck_id')
    if return_puck_id:
        state_params.append(f"puck_id={return_puck_id}")
    
    # Slot position state
    return_slot_position = request.GET.get('return_slot_position')
    if return_slot_position:
        state_params.append(f"slot_position={return_slot_position}")
    
    # Grid position state
    return_grid_position = request.GET.get('return_grid_position')
    if return_grid_position:
        state_params.append(f"grid_position={return_grid_position}")
    
    # Grid ID state
    return_grid_id = request.GET.get('return_grid_id')
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

# Form for the popup action
class CopyGridForm(forms.Form):
    new_box = forms.ModelChoiceField(
        queryset=CryoGridBox.objects.all(),
        label="Box to put duplicated grid in",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    number_to_copy = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Number of times to copy the grid",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.grid = kwargs.pop('grid', None)
        super().__init__(*args, **kwargs)
        
        if self.grid and 'new_box' in self.fields:
            # If initial box value exists, set it
            if hasattr(self.grid, 'grid_box') and self.grid.grid_box:
                self.fields['new_box'].initial = self.grid.grid_box.id

    def clean(self):
        cleaned_data = super().clean()
        new_box = cleaned_data.get('new_box')
        number_to_copy = cleaned_data.get('number_to_copy')
        
        if new_box and number_to_copy:
            # Get used positions in the box
            used_positions = list(CryoGrid.objects.filter(
                grid_box=new_box,
                trashed=False
            ).values_list('position_in_box', flat=True))
            
            # Calculate available positions
            available_positions = sorted(list(
                set(range(1, new_box.max_grids + 1)) - set(used_positions)
            ))
            
            # Check if there are enough positions
            if number_to_copy > len(available_positions):
                self.add_error(
                    'number_to_copy', 
                    f'Box "{new_box}" only has {len(available_positions)} available positions. ' 
                    f'Cannot copy {number_to_copy} grids.'
                )
        
        return cleaned_data
# Custom admin classes for models that need redirect
class PuckAdmin(admin.ModelAdmin):
    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            frontend_url = build_frontend_url_with_state(request)
            return HttpResponseRedirect(frontend_url)
    
    def response_change(self, request, obj):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            frontend_url = build_frontend_url_with_state(request)
            return HttpResponseRedirect(frontend_url)
    
    def response_delete(self, request, obj_display, obj_id):
        frontend_url = build_frontend_url_with_state(request)
        return HttpResponseRedirect(frontend_url)

class CryoGridBoxAdmin(admin.ModelAdmin):
    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            frontend_url = build_frontend_url_with_state(request)
            return HttpResponseRedirect(frontend_url)
    
    def response_change(self, request, obj):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            frontend_url = build_frontend_url_with_state(request)
            return HttpResponseRedirect(frontend_url)
    
    def response_delete(self, request, obj_display, obj_id):
        frontend_url = build_frontend_url_with_state(request)
        return HttpResponseRedirect(frontend_url)

class CryoGridAdmin(admin.ModelAdmin):
    change_form_template = "cryo_grids/change_form.html"
    
    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            frontend_url = build_frontend_url_with_state(request)
            return HttpResponseRedirect(frontend_url)
    
    def response_change(self, request, obj):
        if "_addanother" not in request.POST and "_continue" not in request.POST:
            frontend_url = build_frontend_url_with_state(request)
            return HttpResponseRedirect(frontend_url)
    
    def response_delete(self, request, obj_display, obj_id):
        frontend_url = build_frontend_url_with_state(request)
        return HttpResponseRedirect(frontend_url)

    def run_custom_action(self, request, object_id):
        obj = self.get_object(request, object_id)

        # If GET parameters include duplication data, process the copy action.
        if 'new_box' in request.GET and 'number_to_copy' in request.GET:
            form = CopyGridForm(request.GET, grid=obj)
            if form.is_valid():
                new_box = form.cleaned_data['new_box']
                number_to_copy = form.cleaned_data['number_to_copy']
                print(number_to_copy)
                try:
                    used_positions = list(
                        CryoGrid.objects.filter(
                            grid_box=new_box,
                            trashed=False
                        ).values_list('position_in_box', flat=True)
                    )

                    max_grids = new_box.max_grids or 4  # Default to 4 if not set
                    available_positions = sorted(list(
                        set(range(1, max_grids + 1)) - set(used_positions)
                    ))

                    # Check if there are enough positions for the requested number of copies.
                    if number_to_copy > len(available_positions):
                        error_msg = (
                            f'Box "{new_box}" only has {len(available_positions)} available positions. '
                            f"Cannot copy {number_to_copy} grids."
                        )
                        return render(request, 'cryo_grids/copy_grid_popup.html', {
                            'title': f"Duplicate Grid: {obj.name}",
                            'object': obj,
                            'form': form,
                            'opts': self.model._meta,
                            'error_message': error_msg,
                            'available_positions': available_positions,
                            'max_positions': len(available_positions),
                        })

                    if not available_positions:
                        error_msg = f'Box "{new_box}" has no available positions. Choose a different box.'
                        return render(request, 'cryo_grids/copy_grid_popup.html', {
                            'title': f"Duplicate Grid: {obj.name}",
                            'object': obj,
                            'form': form,
                            'opts': self.model._meta,
                            'error_message': error_msg,
                            'available_positions': [],
                            'max_positions': 0,
                        })

                    # Create copies for the requested number of grids.
                    new_grid_ids = []
                    for position in available_positions[:number_to_copy]:
                        new_grid = _save_copied_grid(obj, new_box, position)
                        new_grid_ids.append(new_grid.id)

                    if len(new_grid_ids) == 1:
                        messages.success(
                            request,
                            f"Grid duplicated successfully! New grid ID: {new_grid_ids[0]}"
                        )
                    else:
                        messages.success(
                            request,
                            f"Created {len(new_grid_ids)} copies of the grid! IDs: {', '.join(map(str, new_grid_ids))}"
                        )

                    return render(request, 'cryo_grids/copy_grid_popup.html', {
                        'title': "Success",
                        'object': obj,
                        'form': form,
                        'opts': self.model._meta,
                        'success': True,
                    })

                except Exception as e:
                    return render(request, 'cryo_grids/copy_grid_popup.html', {
                        'title': f"Duplicate Grid: {obj.name}",
                        'object': obj,
                        'form': form,
                        'opts': self.model._meta,
                        'error_message': f"Failed to duplicate grid: {str(e)}",
                        'available_positions': [],
                        'max_positions': 0,
                    })
            else:
                # Form validation failed; try to compute available positions for the selected box.
                available_positions = []
                max_positions = 0
                box_id = request.GET.get('new_box')
                if box_id:
                    try:
                        box = CryoGridBox.objects.get(id=box_id)
                        max_grids = box.max_grids or 4
                        used_positions = list(
                            CryoGrid.objects.filter(
                                grid_box=box,
                                trashed=False
                            ).values_list('position_in_box', flat=True)
                        )
                        available_positions = sorted(list(
                            set(range(1, max_grids + 1)) - set(used_positions)
                        ))
                        max_positions = len(available_positions)
                    except Exception as e:
                        print(f"Error calculating available positions: {e}")
                return render(request, 'cryo_grids/copy_grid_popup.html', {
                    'title': f"Duplicate Grid: {obj.name}",
                    'object': obj,
                    'form': form,
                    'opts': self.model._meta,
                    'error_message': "Please correct the errors below.",
                    'available_positions': available_positions,
                    'max_positions': max_positions,
                })

        # If no duplication parameters are provided, simply render the form.
        else:
            available_positions = []
            max_positions = 0

            # Get all available boxes and use the current grid's box or the first box as the default.
            all_boxes = CryoGridBox.objects.all()
            initial_box = obj.grid_box or (all_boxes.first() if all_boxes.exists() else None)

            if initial_box:
                max_grids = initial_box.max_grids or 4
                used_positions = list(
                    CryoGrid.objects.filter(
                        grid_box=initial_box,
                        trashed=False
                    ).values_list('position_in_box', flat=True)
                )
                all_positions = list(range(1, max_grids + 1))
                available_positions = [pos for pos in all_positions if pos not in used_positions]
                max_positions = len(available_positions)

                # Debug output (optional)
                print(f"Box: {initial_box.name}, Max grids: {max_grids}")
                print(f"Used positions: {used_positions}")
                print(f"Available positions: {available_positions}")
                print(f"Max positions: {max_positions}")

            # Prepopulate the form with the initial box if available.
            form = CopyGridForm(initial={'new_box': initial_box.id if initial_box else None}, grid=obj)

            context = {
                'title': f"Duplicate Grid: {obj.name}",
                'object': obj,
                'form': form,
                'opts': self.model._meta,
                'available_positions': available_positions,
                'max_positions': max_positions,
            }
            return render(request, 'cryo_grids/copy_grid_popup.html', context)

    def get_urls(self):
        """Register the custom URL for the duplication action."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/duplicate/',
                self.admin_site.admin_view(self.run_custom_action),
                name='cryo_grid_run_action',
            ),
        ]
        logger.debug(f"Custom URLs registered: {custom_urls}")
        return custom_urls + urls

# Register models with custom admin classes
admin.site.register(CryoGrid, CryoGridAdmin),
admin.site.register(Puck, PuckAdmin)
admin.site.register(CryoGridBox, CryoGridBoxAdmin)