from django.forms import ModelForm

from .models import MsiSession, ScreenSessionGroup, SessionPlan


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
