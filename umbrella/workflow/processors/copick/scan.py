"""SSH scan of a copick project (picks / segmentations / meshes).

Runs on the cluster - copick isn't in Embrella, and configs use HPC filesystem paths.
"""

import json
import logging
import shlex
import uuid

from common import clusterio

logger = logging.getLogger(__name__)

COPICK_CONDA_ENV = "/hpc/projects/group.czii/krios1.processing/software/dataportalenv"
COPICK_CONFIG_PATH = "/hpc/projects/group.czii/krios1.processing/copick/{session}/{run}/config.json"

EMPTY = {"picks": [], "segmentations": [], "meshes": []}
_SCAN_PY = r"""
import json, sys
import copick

def _dump(run):
    picks, segs, meshes = [], [], []
    rn = run.name
    for p in (run.picks or []):
        pts = getattr(p, "points", None)
        picks.append({
            "run_name": rn,
            "object_name": getattr(p, "pickable_object_name", None),
            "user_id": p.user_id,
            "session_id": p.session_id,
            "count": len(pts) if pts is not None else None,
        })
    for s in (run.segmentations or []):
        segs.append({
            "run_name": rn,
            "name": getattr(s, "name", None),
            "user_id": s.user_id,
            "session_id": s.session_id,
            "voxel_size": getattr(s, "voxel_size", None),
        })
    for m in (run.meshes or []):
        meshes.append({
            "run_name": rn,
            "object_name": getattr(m, "pickable_object_name", None) or getattr(m, "name", None),
            "user_id": m.user_id,
            "session_id": m.session_id,
        })
    return picks, segs, meshes

out = {"picks": [], "segmentations": [], "meshes": []}
try:
    root = copick.from_file(sys.argv[1])
    for run in root.runs:
        try:
            p, s, m = _dump(run)
            out["picks"] += p
            out["segmentations"] += s
            out["meshes"] += m
        except Exception as e:
            out.setdefault("warnings", []).append("run %s: %s" % (getattr(run, "name", "?"), e))
except Exception as e:
    out = {"error": str(e)}
print("COPICK_SCAN_JSON:" + json.dumps(out))
"""


def scan_copick_project(cluster_id: str, config_path: str, *, timeout: int = 120) -> dict:
    """SSH to `cluster_id`, run copick over `config_path`, return {picks, segmentations, meshes}."""
    try:
        ssh = clusterio.get_cluster_ssh_connection(cluster_id=cluster_id)
    except clusterio.SSHDisabledError:
        return {**EMPTY, "scanned": False, "reason": "ssh_disabled"}
    except Exception:
        logger.exception("copick scan: SSH connect failed for cluster %s", cluster_id)
        return {**EMPTY, "scanned": False, "reason": "ssh_error"}

    # uuid so concurrent scans don't share / collide on the same /tmp script
    remote_script = f"/tmp/copick_scan_{uuid.uuid4().hex}.py"
    try:
        sftp = ssh.open_sftp()
        try:
            with sftp.file(remote_script, "w") as f:
                f.write(_SCAN_PY)
        finally:
            sftp.close()

        cmd = (
            f"ml load anaconda 2>/dev/null; "
            f"conda activate {shlex.quote(COPICK_CONDA_ENV)} && "
            f"python {shlex.quote(remote_script)} {shlex.quote(config_path)}; "
            f"rm -f {shlex.quote(remote_script)}"
        )
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace").strip()

        # copick/conda print noise to stdout; pull our marked line out.
        line = next((ln for ln in out.splitlines() if ln.startswith("COPICK_SCAN_JSON:")), None)
        if line is None:
            logger.error("copick scan: no JSON in output. stderr=%s", err[:500])
            return {**EMPTY, "scanned": False, "reason": "no_output"}

        data = json.loads(line[len("COPICK_SCAN_JSON:") :])
        if "error" in data:
            logger.error("copick scan: copick error: %s", data["error"])
            return {**EMPTY, "scanned": False, "reason": data["error"]}
        return {**EMPTY, **data, "scanned": True}
    except Exception:
        logger.exception("copick scan failed for %s on %s", config_path, cluster_id)
        return {**EMPTY, "scanned": False, "reason": "scan_error"}
    finally:
        ssh.close()


def annotated_run_names(scan: dict) -> list[str]:
    """Distinct copick run names that have at least one annotation."""
    runs: set[str] = set()
    for kind in ("picks", "segmentations", "meshes"):
        for entry in scan.get(kind) or []:
            run_name = entry.get("run_name")
            if run_name:
                runs.add(run_name)
    return sorted(runs)
