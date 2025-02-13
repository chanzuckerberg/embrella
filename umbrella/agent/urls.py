from django.urls import path

from . import views


app_name = 'chatbot'

urlpatterns = [
    path("confluence/", views.api_answer, name = 'llm output')
]