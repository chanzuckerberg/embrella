from django.contrib.auth.models import User
from django.db import models
from external_links.models import ExternalResource
from projects.models import Project

from umbrella.choices import CANE_COLORS, GRID_BOX_COLORS, GRID_BOX_NUMBERING, GRID_CASSETTE_NUMBERING, PUCK_COLORS


class Site(models.Model):
    name = models.CharField(max_length=20, default='3400Bridge', unique=True)
    address = models.CharField(max_length=100,default='')

    def __str__(self):
        return self.name

class Dewar(models.Model):
    name = models.CharField(max_length=20, unique=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    shipper = models.BooleanField(default=False,help_text="Is this a dry-shipper ?")
    max_canes = models.PositiveSmallIntegerField(default=6, help_text="Maximum number of canes fit in the dewar")

    def __str__(self):
        return 'Dewar %s' % self.name

class Cane(models.Model):
    name = models.CharField(max_length=20)
    color = models.CharField(max_length=40, choices=CANE_COLORS, default='CF1E01')
    dewar = models.ForeignKey(Dewar, on_delete=models.CASCADE, null=True, blank=True)
    position_in_dewar = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    max_pucks = models.PositiveSmallIntegerField(default=10, help_text="Maximum number of pucks fit in the cane")

    class Meta:
        unique_together = [["name","color"],["dewar","position_in_dewar"]]

    def __str__(self):
        return 'Cane %s in color %s' % (self.name, self.get_color_display())

class Puck(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=40, choices=PUCK_COLORS, default='CF1E01')

    cane = models.ForeignKey(Cane, on_delete=models.CASCADE, null=True, blank=True)
    # position on cane with 1 at the top.
    position_in_cane = models.PositiveSmallIntegerField(default=1, null=True, blank=True, help_text="position 1 is at the top of the cane")
    max_boxes = models.PositiveSmallIntegerField(default=12, help_text="Maximum number of boxes fit on the puck")
    # NEW: Add user foreign key
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='User who created or is responsible for this puck',
    )

    class Meta:
        unique_together = [["name","color"],["cane","position_in_cane"]]

    def __str__(self):
        return 'Puck %s in color %s' % (self.name, self.get_color_display())

class CryoGridBox(models.Model):
    name = models.CharField(max_length=100, unique=False)
    color = models.CharField(max_length=40, choices=GRID_BOX_COLORS, default='FFFFFF')
    # numbering format with notch at 12-oclock.
    numbering = models.CharField(max_length=20, choices=GRID_BOX_NUMBERING, default='ucw',help_text="numbering system with notch at 12-o'clock orientation")
    puck = models.ForeignKey(Puck, on_delete=models.CASCADE, null=True, blank=True)
    position_in_puck = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    max_grids = models.PositiveSmallIntegerField(default=4, help_text="Maximum number of grids fit in the box")

    class Meta:
        unique_together = [["puck","position_in_puck","name"]]

    def __str__(self):
        # return 'Cryo grid box %s in color %s and %s numbering' % (self.name, self.get_color_display(), self.get_numbering_display())
        puck_info = f" (Puck: {self.puck.name})" if self.puck else " (No Puck)"
        return f'{self.name} in color {self.get_color_display()}{puck_info}'

class CryoGridCassette(models.Model):
    name = models.CharField(max_length=20, unique=True)
    numbering = models.CharField(max_length=3, choices=GRID_CASSETTE_NUMBERING, default='bot',help_text="numbering system on the cassette")
    max_slots = models.PositiveSmallIntegerField(default=12, null=True, blank=True,help_text="number of slots available for grids")

    def __str__(self):
        return 'Cryo cassette %s' % (self.name)

class PlungeFreezingDevice(models.Model):
    name = models.CharField(max_length=100, unique=True)
    maker_model = models.CharField(max_length=32, default='Leica GP2')
    site = models.ForeignKey(Site, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class PlungeFreezingSession(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL,null=True)
    device = models.ForeignKey(PlungeFreezingDevice, on_delete=models.CASCADE)
    device_temperature = models.FloatField(default=4.0, help_text='Temperature of the freezing chamber in degree Celsius')
    humidity = models.PositiveSmallIntegerField(default=95)
    # number_of_grids = models.PositiveSmallIntegerField(default=1)

    # Unified documentation field
    documentation_page = models.ForeignKey(
        ExternalResource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='freezing_session_docs',
        limit_choices_to={'resource_type': 'doc_page'},
        help_text='Documentation page for freezing session (Confluence, Benchling, etc.)'
    )

    def __str__(self):
        date_str = self.datetime.date().isoformat()
        username = self.user.username.split("@")[0] if self.user and self.user.username else "unknown"
        return f"{date_str}-{username}-{self.id}"
    
class Sample(models.Model):
    name = models.CharField(max_length=150, unique=True,help_text='unique sample name that you may use to search your grid for later. For example, lysosome')
    ontology = models.CharField(max_length=32, blank=True,help_text='ontology name and values to help database deposition. For example: "GO:0005764" for lysosome')

    def __str__(self):
        return self.name
    
class Specimen(models.Model):

    samples = models.ManyToManyField(
        Sample,
        blank=True,
        help_text='Associated samples from the Sample',
    )

    # Unified documentation field
    documentation_page = models.ForeignKey(
        ExternalResource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='specimen_docs',
        limit_choices_to={'resource_type': 'doc_page'},
        help_text='Documentation page for sample prep (Confluence, Benchling, etc.)'
    )

    notes = models.TextField(max_length=255, blank=True)


    def __str__(self):
        sample_names = ", ".join(sample.name for sample in self.samples.all())
        return f"Specimen ({sample_names})" if sample_names else "Specimen (no samples)"


class CryoGrid(models.Model):
    create_on = models.DateField(auto_now_add=True)
    updated_on = models.DateField(auto_now=True)
    name = models.CharField(max_length=32, default='grid1')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(max_length=255, blank=True, null=True,help_text='notes about freezing and grid condition on this grid')
    freezing_session = models.ForeignKey(PlungeFreezingSession,blank=True, null=True, on_delete=models.CASCADE, help_text='who and when the grid was frozen')
    specimen = models.ForeignKey(Specimen, on_delete=models.CASCADE, blank=True, null=True, help_text='referring to specimen')
    grid_box = models.ForeignKey(CryoGridBox, on_delete=models.CASCADE, null=True, blank=True, help_text='cryo grid box fit in pucks')
    position_in_box = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    clipped = models.BooleanField(default=False,help_text="Is this cryo-grid clipped ?")
    grid_cassette = models.ForeignKey(CryoGridCassette, on_delete=models.CASCADE, null=True, blank=True, help_text='choose a microscope grid loader cassette when in use')
    slot_number_in_cassette = models.PositiveSmallIntegerField(default=1, null=True, blank=True, help_text='The slot the grid is put in the cryo cassette if exists')
    trashed = models.BooleanField(default=False,help_text="Is this cryo-grid discarded ?")
    intended_project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, help_text='Optionally assign the project this grid is made for. This makes the grid easier to find.')
    copy_number = models.PositiveSmallIntegerField(default=1)
    blot_time = models.FloatField(default=6.0,null=True, help_text='Blot time in seconds')
    blot_force = models.FloatField(default=0.0, blank=True,null=True,help_text='Blot force')
    blot_distance = models.FloatField(default=0.0, blank=True, null=True, help_text="Blot distance")
    resource_link = models.URLField(max_length=200, blank=True, null=True, help_text='Link to additional resources related to this cryo-grid')

    class Meta:
        unique_together = ["name","freezing_session","specimen","copy_number"]
        constraints = [
            models.UniqueConstraint(fields=["grid_box","position_in_box"], name="unique_box_position", condition=models.Q(trashed=False), nulls_distinct=True),
            models.UniqueConstraint(fields=["grid_cassette","slot_number_in_cassette"], name="unique_cassette_slot", condition=models.Q(trashed=False), nulls_distinct=True),
        ]
        
    def __str__(self):
        return '%s.c%d (id=%d) from %s of %s' % (self.name, self.copy_number, self.pk, self.freezing_session, self.specimen)


