from django.urls import path
from . import views

app_name = "workflow"

urlpatterns = [
    path("get_aretomo3", views.get_aretomo3_json, name='json_aretomo3'),
]