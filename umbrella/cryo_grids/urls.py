from django.urls import path

from . import views

#register app namespace
app_name = "cryo_grids"

urlpatterns = [
    path("detail", views.grid_boxes_view, name="detail"),
    path('all_grid_boxes/', views.get_all_grid_boxes, name='get_all_grid_boxes'),
    path('specific_grids/', views.get_specific_grids, name='get_specific_grids'),
    path('v1/grids/', views.get_cryo_grids_details, name='get_cryo_grids_details'),
    path('v1/filterlist', views.available_filters, name='available_filters'),
    path("grid_detail/<int:grid_id>/", views.grid_detail_view, name="grid_detail"),
    # adding a pattern with error_msg in url is a work-around for a Django bug
    # not able to pass kwargs to views. AC
    path('grid_detail/<int:grid_id>/<str:error_msg>/', views.grid_detail_view, name='grid_detail'),
    path('copy_grid_to_box/', views.copy_grid_to_box, name='copy_grid_to_box'),
    path('clear_cassette/', views.clear_cassette_view, name='clear_cassette'),
    path('clear_cassette_filter/<int:cassette_id>/', views.clear_cassette_filter, name='clear_cassette_filter'),
    path('clear_cassette_move/', views.clear_cassette_move, name='clear_cassette_move'),
    path('get_available_box/', views.get_available_positions, name='get'),
    path('available-positions/<int:object_id>', 
         views.get_available_positions, 
         name='get_available_positions'),
]
