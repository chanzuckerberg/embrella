from django.urls import path

from . import views

#register app namespace
app_name = "cryo_grids"

urlpatterns = [
    path("grid_detail/<int:grid_id>/", views.grid_detail_view, name="grid_detail"),
    # adding a pattern with error_msg in url is a work-around for a Django bug
    # not able to pass kwargs to views. AC
    path('grid_detail/<int:grid_id>/<str:error_msg>/', views.grid_detail_view, name='grid_detail'),
    path('copy_grid_to_box/', views.copy_grid_to_box, name='copy_grid_to_box'),
    path('get_available_box/', views.get_available_positions, name='get'),
    path('available-positions/<int:object_id>',
         views.get_available_positions,
         name='get_available_positions'),
    path('update-grid-trashed/<int:grid_id>/', views.update_grid_trashed_status, name='update_grid_trashed_status'),
    path('update-grid-clipped/<int:grid_id>/', views.update_grid_clipped_status, name='update_grid_clipped_status'),
]
