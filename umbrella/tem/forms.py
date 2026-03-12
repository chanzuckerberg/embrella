from django import forms
from django.forms import ModelForm

from .models import MsiSession, ScreenSessionGroup, SessionPlan, User


class ReserveMsiSessionForm(ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.all())

    class Meta:
        model = MsiSession
        fields = ["session_plan", "project", "grid", "user", "magnification"]

    def __init__(self, **kwargs):
        super(ReserveMsiSessionForm, self).__init__(**kwargs)
        self.fields["session_plan"].queryset = SessionPlan.objects.filter(
            imaging_workflow__workflow__in=["tomo", "sngl"]
        )


class MsiSessionForm(ModelForm):
    class Meta:
        model = MsiSession
        fields = "__all__"


class UpdateNotesForm(ModelForm):
    class Meta:
        model = MsiSession
        fields = ["atlas_session", "notes", "project", "magnification"]


class ReserveScreenSessionGroupForm(ModelForm):
    class Meta:
        model = ScreenSessionGroup
        fields = ["session_plan", "cassette", "order"]

    def __init__(self, **kwargs):
        super(ReserveScreenSessionGroupForm, self).__init__(**kwargs)
        self.fields["session_plan"].queryset = SessionPlan.objects.filter(imaging_workflow__workflow="scrn")


class ScreenSessionGroupForm(ModelForm):
    class Meta:
        model = ScreenSessionGroup
        fields = "__all__"


class UpdateOrderForm(ModelForm):
    class Meta:
        model = ScreenSessionGroup
        fields = ["order"]
