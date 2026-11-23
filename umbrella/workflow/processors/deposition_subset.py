"""Resolve typed subset CSVs to positions present in each session's AreTomo metrics."""

import csv
import io
import os
import stat
import sys
import tempfile
from pathlib import Path

import yaml

# Cap the read; a metrics CSV is tiny, so a huge or endless file can't fill memory.
MAX_CSV_MB = 10
MAX_CSV_BYTES = MAX_CSV_MB * 1024 * 1024


def _positions(path, *, source="subset CSV"):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                sys.exit(f"The {source} at {path} is not a regular file.")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                raw = handle.read(MAX_CSV_BYTES + 1)
        finally:
            os.close(fd)
    except OSError as error:
        sys.exit(f"Could not read {source} at {path}: {error}")
    if len(raw) > MAX_CSV_BYTES:
        sys.exit(f"The {source} at {path} exceeds the {MAX_CSV_MB} MB limit.")
    try:
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        positions = [name for name in ((r.get("Tilt_Series") or "").strip().removesuffix(".mrc") for r in rows) if name]
    except (UnicodeDecodeError, csv.Error) as error:
        sys.exit(f"Could not parse {source} at {path}: {error}")
    if not positions:
        sys.exit(f'The {source} at {path} has no tilt series - it needs a "Tilt_Series" column.')
    return positions


def _write(config_path, config):
    """Replace the config atomically, keeping its group-writable staging mode."""
    mode = stat.S_IMODE(os.stat(config_path).st_mode)
    handle, tmp = tempfile.mkstemp(dir=os.path.dirname(config_path) or ".", suffix=".tmp")
    try:
        with os.fdopen(handle, "w") as out:
            yaml.safe_dump(config, out, sort_keys=False, allow_unicode=True)
        os.chmod(tmp, mode)
        os.replace(tmp, config_path)
    except BaseException:
        os.unlink(tmp)
        raise


def resolve(config_path):
    with open(config_path) as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        return
    changed = False
    for dataset in config.get("datasets", {}).values():
        for name, session in dataset.get("sessions", {}).items():
            path = (session.get("subset_csv_path") or "").strip()
            if not path:
                continue
            aretomo_dir = session.get("paths", {}).get("aretomo3")
            if not aretomo_dir:
                sys.exit(f"Session {name} has no AreTomo source path for its tilt series metrics.")
            metrics = Path(aretomo_dir) / "TiltSeries_Metrics.csv"
            available = set(_positions(metrics, source=f"tilt series metrics for session {name}"))
            requested = list(dict.fromkeys(_positions(path)))
            positions = [position for position in requested if position in available]
            if not positions:
                sys.exit(f"Session {name}: none of the positions in {path} match this session's tilt series.")
            skipped = len(requested) - len(positions)
            if skipped:
                print(
                    f"Warning: skipped {skipped} of {len(requested)} requested positions absent from "
                    f"session {name}'s tilt series.",
                    file=sys.stderr,
                )
            session.pop("subset_csv_path")
            session["positions"] = positions
            changed = True
    if changed:
        _write(config_path, config)


if __name__ == "__main__":
    resolve(*sys.argv[1:])
