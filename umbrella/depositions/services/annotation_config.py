"""Translate saved annotation selections into the deposition-prep sync contract."""

import hashlib

from processes.services.cluster_resolver import cluster_id_for_run
from workflow.processors import get_processor

from depositions.services.exceptions import SubmissionValidationError

KINDS = {"picks": "picks", "segmentations": "segmentation_mask"}


def session_annotations(session, authors):
    selected = list(session.annotations.filter(is_selected=True).prefetch_related("method_links").order_by("pk"))
    if not selected:
        return []
    label = session.msi_session.name
    if not session.selected_copick_runs:
        raise SubmissionValidationError(f"Session {label}: select a Copick configuration for annotation export.")
    tomograms = list(session.tomogram_metadata.all())
    default = next((t for t in tomograms if t.is_visualization_default), None)
    if default is None and len(tomograms) == 1:
        default = tomograms[0]
    spacing = default.voxel_spacing if default else None
    if spacing is None or spacing <= 0:
        raise SubmissionValidationError(f"Session {label}: choose a default tomogram with positive voxel spacing.")
    annotations = []
    for annotation in selected:
        kind = KINDS.get(annotation.copick_kind)
        if kind is None:
            raise SubmissionValidationError(f"Session {label}: mesh annotation export is not supported.")
        object_id = annotation.object_id.strip()
        object_name = annotation.object_name.strip()
        method = annotation.annotation_method.strip()
        software = annotation.annotation_software.strip()
        if not all((object_id, object_name, method, software)):
            raise SubmissionValidationError(
                f"Session {label}: selected annotations need an object name, ontology ID, method and software."
            )
        identity = f"{annotation.copick_kind}:{annotation.copick_ref}"
        suffix = hashlib.sha256(identity.encode()).hexdigest()[:12]
        # Stable across sessions and edits; distinct references must not overwrite each other's exports.
        entry = {
            "name": f"annotation_{suffix}",
            "kind": kind,
            "object": {"id": object_id, "name": object_name},
            "copick_ref": annotation.copick_ref,
            "voxel_spacing": spacing,
            "method": method,
            "software": software,
            # Annotation-specific author editing is not available; inherit reviewed dataset authors.
            "authors": authors,
            "ground_truth_status": annotation.ground_truth_status,
            "method_links": [
                {
                    "link_type": link.link_type,
                    "link": link.link,
                    **({"custom_name": link.custom_name} if link.custom_name else {}),
                }
                for link in annotation.method_links.all()
            ],
        }
        if annotation.method_type:
            entry["method_type"] = annotation.method_type
        annotations.append(entry)
    aretomo_run = session.aretomo_run_name
    cluster = cluster_id_for_run(label, aretomo_run if aretomo_run.startswith("run") else f"run{aretomo_run}")
    base = get_processor("copick").get_processing_base_path(cluster=cluster).rstrip("/")
    configs = [f"{base}/{label}/{copick_run}/config.json" for copick_run in session.selected_copick_runs]
    for entry in annotations:
        entry["copick_config"] = configs
    return annotations
