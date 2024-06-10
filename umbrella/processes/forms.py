from django.db import models
from django.forms import ModelForm
from .models import ProcRun

class ReserveProcRunForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = ["proc_plan","msi_session","name"]

class ProcRunForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = "__all__"

class UpdateNotesForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = ["notes",]
