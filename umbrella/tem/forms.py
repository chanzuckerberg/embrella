from django.db import models
from django.forms import ModelForm
from .models import Session
class ReserveSessionForm(ModelForm):
    class Meta:
        model = Session
        fields = ["session_plan","project","grid"]

class SessionForm(ModelForm):
    class Meta:
        model = Session
        fields = "__all__"

class UpdateNotesForm(ModelForm):
    class Meta:
        model = Session
        fields = ["notes"]
