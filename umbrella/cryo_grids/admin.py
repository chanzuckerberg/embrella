from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django import forms
import datetime
import logging

from .models import Site, Dewar, Cane, Puck, CryoGridBox, CryoGridCassette
from .models import PlungeFreezingDevice, PlungeFreezingSession, Specimen, CryoGrid, Sample
from .views import _save_copied_grid, get_available_positions

logger = logging.getLogger(__name__)

# Register standard models
admin.site.register(Site)
admin.site.register(Dewar)
admin.site.register(Cane)
admin.site.register(Puck)
admin.site.register(CryoGridBox)
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

# Custom admin for CryoGrid
class CryoGridAdmin(admin.ModelAdmin):
    change_form_template = "cryo_grids/change_form.html"
    
    def run_custom_action(self, request, object_id):
        """Function to handle the button click."""
        obj = self.get_object(request, object_id)
        
        if request.method == 'POST':
            form = CopyGridForm(request.POST, grid=obj)
            if form.is_valid():
                # Process the form data
                new_box = form.cleaned_data['new_box']
                number_to_copy = form.cleaned_data['number_to_copy']
                
                try:
                    # Get used positions in the box
                    used_positions = list(CryoGrid.objects.filter(
                        grid_box=new_box,
                        trashed=False
                    ).values_list('position_in_box', flat=True))
                    
                    # Calculate available positions
                    max_grids = new_box.max_grids or 4  # Default to 4 if max_grids is None
                    available_positions = sorted(list(
                        set(range(1, max_grids + 1)) - set(used_positions)
                    ))
                    
                    # Check if there are enough available positions
                    if number_to_copy > len(available_positions):
                        error_msg = f'Box "{new_box}" only has {len(available_positions)} available positions. Cannot copy {number_to_copy} grids.'
                        return render(request, 'cryo_grids/copy_grid_popup.html', {
                            'title': f"Duplicate Grid: {obj.name}",
                            'object': obj,
                            'form': form,
                            'opts': self.model._meta,
                            'error_message': error_msg,
                            'available_positions': available_positions,
                            'max_positions': len(available_positions),
                        })
                    
                    # No available positions
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
                    
                    # Create copies
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
                    
                    # Return the same template but with success message
                    return render(request, 'cryo_grids/copy_grid_popup.html', {
                        'title': "Success",
                        'object': obj,
                        'form': form,
                        'opts': self.model._meta,
                        'success': True,
                    })
                    
                except Exception as e:
                    # Return to popup with error message
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
                # Form validation failed, stay in the popup
                # Get available positions for the selected box
                available_positions = []
                max_positions = 0
                box_id = request.POST.get('new_box')
                if box_id:
                    try:
                        box = CryoGridBox.objects.get(id=box_id)
                        max_grids = box.max_grids or 4  # Default to 4 if max_grids is None
                        used_positions = list(CryoGrid.objects.filter(
                            grid_box=box, 
                            trashed=False
                        ).values_list('position_in_box', flat=True))
                        
                        available_positions = sorted(list(
                            set(range(1, max_grids + 1)) - set(used_positions)
                        ))
                        max_positions = len(available_positions)
                    except Exception as e:
                        print(f"Error calculating available positions: {e}")
                
                # Render the form with errors
                return render(request, 'cryo_grids/copy_grid_popup.html', {
                    'title': f"Duplicate Grid: {obj.name}",
                    'object': obj,
                    'form': form,  # This contains the validation errors
                    'opts': self.model._meta,
                    'error_message': "Please correct the errors below.",
                    'available_positions': available_positions,
                    'max_positions': max_positions,
                })
        
        # For GET request, calculate available positions for initial box
        available_positions = []
        max_positions = 0
        
        # Get all boxes for selection
        all_boxes = CryoGridBox.objects.all()
        
        # If a box is selected (either the grid's box or first available)
        initial_box = obj.grid_box or (all_boxes.first() if all_boxes.exists() else None)
        
        if initial_box:
            # Calculate available positions more carefully
            max_grids = initial_box.max_grids
            if not max_grids or max_grids <= 0:
                max_grids = 4  # Default to 4 if max_grids is invalid
                
            # Get all positions already used in this box
            used_positions = list(CryoGrid.objects.filter(
                grid_box=initial_box,
                trashed=False  # Only count non-trashed grids
            ).values_list('position_in_box', flat=True))
            
            # Calculate available positions
            all_positions = list(range(1, max_grids + 1))
            available_positions = [pos for pos in all_positions if pos not in used_positions]
            max_positions = len(available_positions)
            
            # Debug output (you can remove this later)
            print(f"Box: {initial_box.name}, Max grids: {max_grids}")
            print(f"Used positions: {used_positions}")
            print(f"Available positions: {available_positions}")
            print(f"Max positions: {max_positions}")
        
        # Create the form
        form = CopyGridForm(grid=obj)
        
        # Render the popup form
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
        """Add a custom URL to handle the button action."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/duplicate/',
                self.admin_site.admin_view(self.run_custom_action),
                name='cryo_grid_run_action',
            ),
            path(
                '<path:object_id>/available-positions/',
                self.admin_site.admin_view(get_available_positions),
                name='get_available_positions',
            ),
        ]
        logger.debug(f"Custom URLs registered: {custom_urls}")  # Debug log
        return custom_urls + urls

# Register CryoGrid with the custom admin
admin.site.register(CryoGrid, CryoGridAdmin)
