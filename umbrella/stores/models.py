from django.db import models
from django.contrib.auth.models import User

def fill_place_holders(input_str, key_values={}):
    for k in key_values.keys():
        place_holder = '{%s}' % k
        input_str = input_str.replace(place_holder, key_values[k])
    return input_str

class Path(models.Model):
    static_path = models.CharField(max_length=255, help_text="path referenced in program")
    overlay_path = models.CharField(max_length=255, help_text="filesystem path of the data")
    #path_type = models.CharField(max_length=32, choices=PATH_TYPES,default='dir')

    class Meta:
        app_label = 'stores'

    def fill_place_holders(self, input_str, key_values):
        return fill_place_holders(input_str, key_values)

    def __str__(self):
        return self.static_path

