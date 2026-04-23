from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

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
                ('imod', 'aln in imod compatible format for relion'),
                ('rec','all frame tomo recon'),
                ('evn','even frame tomo recon'),
                ('odd','odd frame tomo recon'),
                ('deno','denoised tomo recon'),
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
        return self.overlay_path

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


class Cluster(models.Model):
    cluster_id = models.CharField(
        max_length=16,
        primary_key=True,
        help_text="Short identifier used in code (e.g. 'czii', 'bruno')",
    )
    name = models.CharField(max_length=64, help_text="Human-readable display name")

    http_base_url = models.CharField(
        max_length=255,
        help_text="Base URL of Caddy server, e.g. https://czii-onsite.czbiohub.org/ (no scope subdir)",
    )

    ssh_hostname = models.CharField(max_length=128)
    ssh_port = models.PositiveIntegerField(default=22)

    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'stores'

    def __str__(self):
        return self.cluster_id


@receiver([post_save, post_delete], sender=Cluster)
def _invalidate_clusterio_cache(sender, **kwargs):
    from common.clusterio import clear_cluster_cache
    clear_cluster_cache()

