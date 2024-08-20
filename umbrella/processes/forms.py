from django.db import models
from django.forms import ModelForm
from .models import select_plan_ids_by_input_data_types
from .models import ProcRun, ProcPlan

class ReserveFrameProcRunForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = ["proc_plan","msi_session"]

    def __init__(self, **kwargs):
        super(ReserveFrameProcRunForm, self).__init__(**kwargs)
        plan_ids = select_plan_ids_by_input_data_types(['frames',])
        self.fields['proc_plan'].queryset = ProcPlan.objects.filter(id__in=plan_ids)

class ReserveTomoProcRunForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = ["proc_plan","msi_session"]

    def __init__(self, **kwargs):
        super(ReserveTomoProcRunForm, self).__init__(**kwargs)
        plan_ids = select_plan_ids_by_input_data_types(['rec','deno','evn'])
        self.fields['proc_plan'].queryset = ProcPlan.objects.filter(id__in=plan_ids)

class ProcRunForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = "__all__"

class UpdateNotesForm(ModelForm):
    class Meta:
        model = ProcRun
        fields = ["notes",]

