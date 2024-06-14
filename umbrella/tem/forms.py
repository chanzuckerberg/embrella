from django.db import models
from django.forms import ModelForm
from .models import MsiSession, ScreenSessionGroup

class ReserveMsiSessionForm(ModelForm):
    class Meta:
        model = MsiSession
        fields = ["session_plan","project","grid"]

class MsiSessionForm(ModelForm):
    class Meta:
        model = MsiSession
        fields = "__all__"

class UpdateNotesForm(ModelForm):
    class Meta:
        model = MsiSession
        fields = ["grid_session","notes"]

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

