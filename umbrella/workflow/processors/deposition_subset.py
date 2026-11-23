"""Job-side subset resolution, embedded in the prep script.
Rewrites a session's typed ``subset_csv_path`` to ``positions`` from its ``Tilt_Series`` column."""

import csv
import os
import stat
import sys
import tempfile

import yaml


def _positions(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as error:
        sys.exit(f"Could not read subset CSV {path}: {error}")
    except (UnicodeDecodeError, csv.Error) as error:
        sys.exit(f"Could not parse subset CSV {path}: {error}")
    names = ((row.get("Tilt_Series") or "").strip().removesuffix(".mrc") for row in rows)
    positions = [name for name in names if name]
    if not positions:
        sys.exit(f'Subset CSV {path} has no tilt series - it needs a "Tilt_Series" column.')
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
        for session in dataset.get("sessions", {}).values():
            path = (session.get("subset_csv_path") or "").strip()
            if not path:
                continue
            session.pop("subset_csv_path")
            session["positions"] = _positions(path)
            changed = True
    if changed:
        _write(config_path, config)


if __name__ == "__main__":
    resolve(*sys.argv[1:])
