from django.urls import path

from . import views

#register app namespace
app_name = "cryo_grids"

urlpatterns = [
    path("detail", views.grid_boxes_view, name="detail"),
    path('all_grid_boxes/', views.get_all_grid_boxes, name='get_all_grid_boxes'),
    path('specific_grids/', views.get_specific_grids, name='get_specific_grids'),
]
