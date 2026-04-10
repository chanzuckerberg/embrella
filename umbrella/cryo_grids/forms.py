from django.forms import Form, IntegerField, ModelForm

from .models import CryoGrid


class CopyGridForm(ModelForm):
    class Meta:
        model = CryoGrid
        fields = ["name", "grid_box", "copy_number"]

class NumberToCopyGridForm(Form):
    number_to_copy = IntegerField(label="Number of times to copy the grid")


