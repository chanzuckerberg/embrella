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
    path('clear_cassette/', views.clear_cassette_view, name='clear_cassette'),
    path('clear_cassette_filter/<int:cassette_id>/', views.clear_cassette_filter, name='clear_cassette_filter'),
    path('clear_cassette_move/', views.clear_cassette_move, name='clear_cassette_move'),
]
