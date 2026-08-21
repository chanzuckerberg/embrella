import logging
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from stores import placeholders

logger = logging.getLogger(__name__)

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


def fill_place_holders(input_str, key_values=None):
    for k, v in (key_values or {}).items():
        input_str = input_str.replace("{%s}" % k, str(v))
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


def validate_path_template(template):
    """Reject a directory template naming a token nothing can substitute."""
    unknown = placeholders.unknown_placeholders(template)
    if not unknown:
        return
    problems = []
    for name in sorted(unknown):
        suggestion = placeholders.suggest_placeholder(name)
        hint = f" Did you mean {{{suggestion}}}?" if suggestion else ""
        problems.append(f"Unknown placeholder {{{name}}}.{hint}")
    legal = ", ".join("{%s}" % n for n in sorted(placeholders.known_placeholders()))
    raise ValidationError(" ".join(problems) + f" Available placeholders: {legal}")


class Path(models.Model):
    overlay_path = models.CharField(max_length=255, help_text="filesystem path of the data")
    # path_type = models.CharField(max_length=32, choices=PATH_TYPES,default='dir')

    class Meta:
        app_label = "stores"

    def fill_place_holders(self, input_str, key_values):
        return fill_place_holders(input_str, key_values)

    def __str__(self):
        return self.overlay_path


class DataKind(models.Model):
    """A kind of data -- the logical handle `Pipe.input` and `resolve_review_path` key on.

    Carries no path of its own: where a kind physically lives is answered by a PathType
    template resolved against a session or run.
    """

    data_type = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.data_type


class PathType(models.Model):
    data_kind = models.ForeignKey(DataKind, on_delete=models.CASCADE)
    overlay_path = models.CharField(max_length=255, help_text="filesystem path with placeholder")
    cluster = models.ForeignKey(
        "stores.Cluster",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Blank is the cluster-agnostic default, and the fallback. A row naming a "
        "cluster overrides that default on that cluster only.",
    )
    # path_type = models.CharField(max_length=32, choices=PATH_TYPES,default='dir')

    class Meta:
        app_label = "stores"

    def fill_place_holders(self, input_str, key_values):
        return fill_place_holders(input_str, key_values)

    def __str__(self):
        suffix = " @%s" % self.cluster_id if self.cluster_id else ""
        return "%s=>%s%s" % (self.data_kind.data_type, self.overlay_path, suffix)

    def clean(self):
        super().clean()
        validate_path_template(self.overlay_path)

    @classmethod
    def resolve(cls, data_type, cluster=None):
        """The PathType for `data_type` on `cluster`, else the cluster-agnostic default.

        Returns None when no row matches at all, so callers can raise their own error.
        """
        rows = list(cls.objects.select_related("data_kind").filter(data_kind__data_type=data_type))
        return pick_for_cluster(rows, cluster)


def pick_for_cluster(path_types, cluster=None):
    """Cluster-specific row if one exists, else the cluster-agnostic default, else None.

    Two independent dimensions -- which template, and which cluster -- each one rung deep.
    """
    rows = list(path_types)
    cluster_id = getattr(cluster, "cluster_id", cluster)
    if cluster_id is not None:
        specific = [pt for pt in rows if pt.cluster_id == cluster_id]
        if specific:
            return _lowest_pk(specific, "cluster %r" % cluster_id)
    default = [pt for pt in rows if pt.cluster_id is None]
    if default:
        return _lowest_pk(default, "the cluster-agnostic default")
    return None


def _lowest_pk(rows, what):
    # Ambiguity should be observable, not silently ranked.
    if len(rows) > 1:
        logger.warning(
            "%d PathType rows match %s (pks %s); using the lowest. Remove the extras.",
            len(rows),
            what,
            ", ".join(str(pt.pk) for pt in rows),
        )
    return min(rows, key=lambda pt: pt.pk)


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

    `data_type`    — DataKind.data_type of the template row (e.g. 'proc_dir', 'zarr_url', 'thumb_url').
    `cluster`      — stores.Cluster instance; supplies {http_base}.
    `msi_session`  — tem.MsiSession instance; supplies {scope} and {msi_session}.
    `backend_fetch`— set True when the *server* (not the browser) will fetch the resulting
                     URL, so it uses the in-network base instead of the browser-facing one.
    `**context`    — additional placeholder values (e.g. workflow, run, position, vol_suffix).
    """
    # Cluster-aware: a bare .get() raised MultipleObjectsReturned the moment a data_type
    # had a per-cluster sibling.
    pt = PathType.resolve(data_type, cluster=cluster)
    if pt is None:
        raise PathType.DoesNotExist(
            f"No PathType for data_type {data_type!r} (cluster {getattr(cluster, 'cluster_id', cluster)!r}). "
            f"Add one in the admin under Stores → Path types."
        )
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
    values = {
        "http_base": http_base,
        "scope": msi_session.session_plan.scope.name,
        "msi_session": msi_session.name,
        **{k: v for k, v in context.items() if v is not None},
    }
    return fill_place_holders(pt.overlay_path, values)
