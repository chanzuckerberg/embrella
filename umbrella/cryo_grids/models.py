from django.db import models
from django.contrib.auth.models import User

from umbrella.choices import CANE_COLORS, PUCK_COLORS
from umbrella.choices import GRID_BOX_COLORS, GRID_BOX_NUMBERING

class Site(models.Model):
    name = models.CharField(max_length=20, default='3400Bridge', unique=True)
    address = models.CharField(max_length=100,default='')

    def __str__(self):
        return self.name

class Dewar(models.Model):
    name = models.CharField(max_length=20, unique=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    shipper = models.BooleanField(default=False,help_text="Is this a dry-shipper ?")

    def __str__(self):
        return 'Dewar %s' % self.name

class Cane(models.Model):
    name = models.CharField(max_length=20)
    color = models.CharField(max_length=40, choices=CANE_COLORS, default='CF1E01')
    dewar = models.ForeignKey(Dewar, on_delete=models.CASCADE, null=True, blank=True)
    position_in_dewar = models.PositiveSmallIntegerField(default=1, null=True, blank=True)

    class Meta:
        unique_together = [["name","color"],["dewar","position_in_dewar"]]

    def __str__(self):
        return 'Cane %s in color %s' % (self.name, self.get_color_display())

class Puck(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=40, choices=PUCK_COLORS, default='CF1E01')

    cane = models.ForeignKey(Cane, on_delete=models.CASCADE, null=True, blank=True)
    # position on cane with 1 at the top.
    position_in_cane = models.PositiveSmallIntegerField(default=1, null=True, blank=True)

    class Meta:
        unique_together = [["name","color"],["cane","position_in_cane"]]

    def __str__(self):
        return 'Puck %s in color %s' % (self.name, self.get_color_display())

class CryoGridBox(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=40, choices=GRID_BOX_COLORS, default='FFFFFF')
    # numbering format with notch at 12-oclock.
    numbering = models.CharField(max_length=20, choices=GRID_BOX_NUMBERING, default='ucw',help_text="numbering system with notch at 12-o'clock orientation")
    puck = models.ForeignKey(Puck, on_delete=models.CASCADE, null=True, blank=True)
    position_in_puck = models.PositiveSmallIntegerField(default=1, null=True, blank=True)

    class Meta:
        unique_together = [["puck","position_in_puck"]]

    def __str__(self):
        return 'Cryo grid box %s in color %s and %s numbering' % (self.name, self.get_color_display(), self.get_numbering_display())

class PlungeFreezingDevice(models.Model):
    name = models.CharField(max_length=100, unique=True)
    maker_model = models.CharField(max_length=32, default='Leica GP2')
    site = models.ForeignKey(Site, on_delete=models.CASCADE,)

    def __str__(self):
        return self.name

class PlungeFreezingSession(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL,null=True)
    device = models.ForeignKey(PlungeFreezingDevice, on_delete=models.CASCADE,)
    device_temperature = models.FloatField(default=4.0, help_text='Temperature of the freezing chamber in degree Celsius')
    humidity = models.PositiveSmallIntegerField(default=95)
    number_of_grids = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return '%s' % self.datetime.date().isoformat()

class Sample(models.Model):
    name = models.CharField(max_length=100, unique=True,help_text='unique sample name that you may use to search your grid for later. For example, lysosome')

    def __str__(self):
        return self.name

class PlungeFreezingPlan(models.Model):
    # may be multiple samples that each needs history and metadata
    sample = models.ManyToManyField(Sample,)
    sample_application_protocol = models.TextField(max_length=255, blank=True)
    blot_time = models.FloatField(default=6.0, help_text='Blot time in seconds')
    wash_step = models.TextField(max_length=255, blank=True)
    tag = models.CharField(max_length=100, blank=True)

    def __str__(self):
        sample_str = ','.join(list(map((lambda x: x['name']),self.sample.values())))
        return '%s with %s, id=%d' % (sample_str, self.tag, self.pk)

class CryoGrid(models.Model):
    create_on = models.DateField(auto_now_add=True)
    name = models.CharField(max_length=32, default='Grid1')
    notes = models.TextField(max_length=255, blank=True, null=True,help_text='notes about freezing and grid condition on this grid')
    freezing_session = models.ForeignKey(PlungeFreezingSession, on_delete=models.CASCADE,)
    freezing_plan = models.ForeignKey(PlungeFreezingPlan, on_delete=models.CASCADE,)
    grid_box = models.ForeignKey(CryoGridBox, on_delete=models.CASCADE,)
    position_in_box = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    clipped = models.BooleanField(default=False,help_text="Is this cryo-grid clipped ?")
    trashed = models.BooleanField(default=False,help_text="Is this cryo-grid discarded ?")

    def __str__(self):
        return '%s from %s with %s' % (self.name, self.freezing_session, self.freezing_plan)

