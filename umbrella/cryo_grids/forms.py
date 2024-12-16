from django.db import models
from django.forms import Form, ModelForm, IntegerField
from .models import CryoGrid, CryoGridCassette
from django import forms

class CopyGridForm(ModelForm):
    class Meta:
        model = CryoGrid
        fields = ["name", "grid_box", "copy_number"]

class NumberToCopyGridForm(Form):
    number_to_copy = IntegerField(label="Number of times to copy the grid")

class ClearCassetteForm(ModelForm):
    class Meta:
        model = CryoGrid
        fields = ["grid_cassette","slot_number_in_cassette","name", "user", "grid_box", "position_in_box"]

