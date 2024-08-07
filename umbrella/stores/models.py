from django.db import models
from django.contrib.auth.models import User

DATA_TYPES = [
                ('atlas','grid atlas'),
                ('satlas','grid atlas from screening'),
                ('parents','parent image of the tomography images'),
                ('sums','sum image of the frames'),
                ('frames','frames'),
                ('rawst','raw tilt image stack'),
                ('tangl','tilt angles'),
                ('mdoc','mdoc'),
                ('ctf','ctf values'),
                ('aln','tilt alignments'),
                ('rec','all frame tomo recon'),
                ('evn','even frame tomo recon'),
                ('odd','odd frame tomo recon'),
                ('pick','particle point annotation'),
                ('seg','segmentation'),
                ('galr','particle gallery'),
            ]

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

class StaticPath(models.Model):
    data_type = models.CharField(max_length=8, choices=DATA_TYPES,unique=True)
    static_path = models.CharField(max_length=255, help_text="path reference with placeholder")
    def __str__(self):
        return self.data_type


class PathType(models.Model):
    static_path = models.ForeignKey(StaticPath, on_delete=models.CASCADE)
    overlay_path = models.CharField(max_length=255, help_text="filesystem path with placeholder")
    #path_type = models.CharField(max_length=32, choices=PATH_TYPES,default='dir')

    class Meta:
        app_label = 'stores'

    def fill_place_holders(self, input_str, key_values):
        return fill_place_holders(input_str, key_values)

    def __str__(self):
        return '%s=>%s' % (self.static_path.data_type, self.overlay_path)

