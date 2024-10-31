from django.db import models
from django.forms import Form, ModelForm
from .models import CryoGrid, CryoGridCassette
from django import forms
class ClearCassetteForm(ModelForm):
    class Meta:
        model = CryoGrid
        fields = ["grid_cassette","slot_number_in_cassette","name", "user", "grid_box", "position_in_box"]

