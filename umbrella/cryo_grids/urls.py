from django.urls import path

from . import views

# register app namespace
app_name = "cryo_grids"

urlpatterns = [
    path("update-grid-trashed/<int:grid_id>/", views.update_grid_trashed_status, name="update_grid_trashed_status"),
    path("update-grid-clipped/<int:grid_id>/", views.update_grid_clipped_status, name="update_grid_clipped_status"),
]
