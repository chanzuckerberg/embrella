from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

DATA_TYPES = [
    ("atlas", "grid atlas"),
    ("satlas", "grid atlas from screening"),
    ("parents", "parent image of the tomography images"),
    ("sums", "sum image of the frames"),
    ("frames", "frames"),
    ("rawst", "raw tilt image stack"),
    ("tangl", "tilt angles"),
    ("mdoc", "mdoc"),
    ("ctf", "ctf values"),
    ("aln", "tilt alignments"),
    ("imod", "aln in imod compatible format for relion"),
    ("rec", "all frame tomo recon"),
    ("evn", "even frame tomo recon"),
    ("odd", "odd frame tomo recon"),
    ("deno", "denoised tomo recon"),
    ("pick", "particle point annotation"),
    ("seg", "segmentation"),
    ("galr", "particle gallery"),
    ("proc_dir", "processing directory on cluster filesystem"),
    ("proc_url", "processing directory URL"),
    ("zarr_url", "zarr volume URL for tomogram viewer"),
    ("thumb_url", "thumbnail/CTF-thumbnail URL base"),
    ("copick_url", "copick project root URL"),
]


def fill_place_holders(input_str, key_values={}):
    for k in key_values.keys():
        place_holder = "{%s}" % k
        input_str = input_str.replace(place_holder, key_values[k])
    return input_str


def validate_fileserver_base_url(url):
    """Reject a cluster base URL whose origin isn't in settings.FILESERVER_ALLOWED_HOSTS.

    The allowlist bounds both the URLs embedded in the frontend and the URLs the
    backend fetches, so a tampered `Cluster.http_base_url` can't point users or the
    server at an arbitrary host (content injection / SSRF). An empty allowlist means
    no restriction. Raises ValidationError on a disallowed origin.
    """
    allowed = settings.FILESERVER_ALLOWED_HOSTS
    if not allowed:
        return
    parsed = urlparse(url or "")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in allowed:
        raise ValidationError(
            f"File-server host '{origin}' is not allowed. Add it to FILESERVER_ALLOWED_HOSTS "
            f"or use one of: {', '.join(allowed)}."
        )


class Path(models.Model):
    static_path = models.CharField(max_length=255, help_text="path referenced in program")
    overlay_path = models.CharField(max_length=255, help_text="filesystem path of the data")
    # path_type = models.CharField(max_length=32, choices=PATH_TYPES,default='dir')

    class Meta:
        app_label = "stores"

    def fill_place_holders(self, input_str, key_values):
        return fill_place_holders(input_str, key_values)

    def __str__(self):
        return self.overlay_path


class StaticPath(models.Model):
    data_type = models.CharField(max_length=16, choices=DATA_TYPES, unique=True)
    static_path = models.CharField(max_length=255, help_text="path reference with placeholder")

    def __str__(self):
        return self.data_type


class PathType(models.Model):
    static_path = models.ForeignKey(StaticPath, on_delete=models.CASCADE)
    overlay_path = models.CharField(max_length=255, help_text="filesystem path with placeholder")
    # path_type = models.CharField(max_length=32, choices=PATH_TYPES,default='dir')

    class Meta:
        app_label = "stores"

    def fill_place_holders(self, input_str, key_values):
        return fill_place_holders(input_str, key_values)

    def __str__(self):
        return "%s=>%s" % (self.static_path.data_type, self.overlay_path)


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
    is_default = models.BooleanField(
        default=False,
        help_text="Fallback cluster for records with no explicit cluster (file URLs, review resolution).",
    )

    class Meta:
        app_label = "stores"

    def __str__(self):
        return self.cluster_id

    def clean(self):
        super().clean()
        validate_fileserver_base_url(self.http_base_url)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Enforce a single default
        if self.is_default:
            Cluster.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    @classmethod
    def get_default(cls):
        """Return the designated default cluster, else the first active one (or None)."""
        return (
            cls.objects.filter(is_default=True).first()
            or cls.objects.filter(is_active=True).order_by("cluster_id").first()
        )


@receiver([post_save, post_delete], sender=Cluster)
def _invalidate_clusterio_cache(sender, **kwargs):
    from common.clusterio import clear_cluster_cache

    clear_cluster_cache()


def resolve_review_path(data_type, cluster, msi_session, *, backend_fetch=False, **context):
    """Resolve a review/metadata PathType template into a concrete URL or filesystem path.

    `data_type`    — StaticPath.data_type of the template row (e.g. 'proc_dir', 'zarr_url', 'thumb_url').
    `cluster`      — stores.Cluster instance; supplies {http_base}.
    `msi_session`  — tem.MsiSession instance; supplies {scope} (lowercased) and {msi_session}.
    `backend_fetch`— set True when the *server* (not the browser) will fetch the resulting
                     URL, so it uses the in-network base instead of the browser-facing one.
    `**context`    — additional placeholder values (e.g. workflow, run, position, vol_suffix).
    """
    pt = PathType.objects.select_related("static_path").get(static_path__data_type=data_type)
    http_base = cluster.http_base_url
    # Only URL templates embed {http_base}; filesystem templates (e.g. proc_dir) don't.
    if "{http_base}" in pt.overlay_path:
        # Defense in depth: re-validate the admin-editable base in case a disallowed
        # value bypassed Cluster.clean() (raw SQL, a restored dump, a data migration).
        validate_fileserver_base_url(cluster.http_base_url)
        # Server-side fetches use the in-network base (trusted deploy setting) so the
        # server can reach the file server even when http_base_url is browser-only.
        if backend_fetch and settings.FILESERVER_INTERNAL_BASE_URL:
            http_base = settings.FILESERVER_INTERNAL_BASE_URL
    scope = msi_session.session_plan.scope.name.lower()
    values = {
        "http_base": http_base,
        "scope": scope,
        "msi_session": msi_session.name,
        **{k: str(v) for k, v in context.items() if v is not None},
    }
    return fill_place_holders(pt.overlay_path, values)
