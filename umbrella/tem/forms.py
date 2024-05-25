from django.db import models
from django.forms import ModelForm
from .models import Session, ScreenSessionGroup

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

class ReserveScreenSessionGroupForm(ModelForm):
    class Meta:
        model = ScreenSessionGroup
        fields = ["session_plan","cassette","order"]

class ScreenSessionGroupForm(ModelForm):
    class Meta:
        model = ScreenSessionGroup
        fields = "__all__"

class UpdateOrderForm(ModelForm):
    class Meta:
        model = ScreenSessionGroup
        fields = ["order"]

