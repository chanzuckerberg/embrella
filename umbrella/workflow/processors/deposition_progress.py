"""Job-side progress reporter, embedded in deposition scripts; no Django dependencies."""

import csv
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path


def prep_inventory(config_path, dataset_id):
    import yaml

    config = yaml.safe_load(Path(config_path).read_text())
    root = Path(config["output_dir"]) / str(dataset_id)
    block = next(b for b in config["datasets"].values() if b["dataset_id"] == int(dataset_id))
    inventory = {}
    # Source -> staged names from deposition_prep.commands.sync.SYMLINK_TYPES.
    links = (
        ("aretomo3", "{pos}.aln", "{run}.aln", "Alignment"),
        ("aretomo3", "{pos}_CTF.txt", "{run}_CTFFIND_format_CTF.txt", "CTF"),
        ("aretomo3", "{pos}.mrc", "{run}_TS.mrc", "Tilt series"),
        ("dctf_vol", "{pos}_Vol.mrc", "{run}_dctf_Vol.mrc", "Tomograms"),
        ("denoise", "{pos}_Vol.mrc", "{run}_Vol.mrc", "Tomograms"),
        ("memseg", "{pos}_Vol_Segment_mask.mrc", "{run}_Vol_Segment_mask.mrc", "Masks"),
        ("mdoc", "{pos}.mdoc", "{run}.mdoc", "Metadata"),
        ("aretomo3", "{pos}_TLT.txt", "{run}_st.rawtlt", "Metadata"),
    )
    for name, session in block["sessions"].items():
        paths = session["paths"]
        prefix = session.get("prefix", name)
        metrics_name = f"{name}_TiltSeries_Metrics.csv"
        candidates = (
            root / metrics_name,
            root.parent / metrics_name,
            Path(paths["aretomo3"]) / "TiltSeries_Metrics.csv",
        )
        metrics = next(p for p in candidates if p.is_file())
        inventory[metrics_name] = "Metadata"
        with metrics.open() as handle:
            positions = [row["Tilt_Series"].removesuffix(".mrc") for row in csv.DictReader(handle)]
        for pos in positions:
            run = f"{prefix}_{pos}"
            for key, source, target, label in links:
                if paths.get(key) and (Path(paths[key]) / source.format(pos=pos)).exists():
                    inventory[target.format(run=run)] = label
            if paths.get("mdoc") and paths.get("frames"):
                mdoc = Path(paths["mdoc"]) / f"{pos}.mdoc"
                if mdoc.is_file():
                    text = mdoc.read_text(errors="replace")
                    for original in re.findall(r"^\s*SubFramePath\s*=\s*(.+?)\s*$", text, re.MULTILINE):
                        filename = original.replace("\\", "/").rsplit("/", 1)[-1]
                        if (Path(paths["frames"]) / filename).is_file():
                            target = filename if filename.startswith(prefix) else f"{prefix}_{filename}"
                            inventory[f"{run}/{target}"] = "Frames"
        if paths.get("gain") and Path(paths["gain"]).is_file():
            inventory[Path(paths["gain"]).name] = "Metadata"
        if positions:
            inventory["run_to_data_map.tsv"] = "Metadata"
            inventory["portal_dataset_config.yaml"] = "Metadata"
    return root, inventory


def staged_files(root):
    files = {}
    for directory, _, names in os.walk(root):
        for name in names:
            path = Path(directory) / name
            files[path.relative_to(root).as_posix()] = path
    return files


def prep_sample(root, inventory, complete):
    files = staged_files(root)
    totals = Counter(inventory.values())
    counts = Counter(inventory[name] for name in files.keys() & inventory.keys())
    sample = {
        "done": sum(counts.values()),
        "total": len(inventory),
        "items": [{"label": label, "done": counts[label], "total": total} for label, total in sorted(totals.items())],
    }
    if complete:
        size = 0
        for path in files.values():
            try:
                size += path.stat().st_size
            except OSError:
                continue
        sample.update(done=len(files), total=len(files), summary={"objects": len(files), "bytes": size})
    return sample


_AWS_PROGRESS = re.compile(r"Completed\s+([\d.,]+)\s*(Bytes|[KMGTPE]?i?B)/([\d.,]+)\s*(Bytes|[KMGTPE]?i?B)")


def transfer_bytes(value, unit):
    power = "KMGTPE".find(unit[0]) + 1 if unit[0] in "KMGTPE" else 0
    return int(float(value.replace(",", "")) * (1024 if "i" in unit else 1000) ** power)


def upload_sample(text):
    matches = list(_AWS_PROGRESS.finditer(text))
    if not matches:
        return None
    done, done_unit, total, total_unit = matches[-1].groups()
    return {"done": transfer_bytes(done, done_unit), "total": transfer_bytes(total, total_unit)}


def write_snapshot(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data))
    os.replace(temporary, path)


def report(phase, snapshot_path, source, dataset_id=None):
    path = Path(snapshot_path)
    stop = Path(f"{snapshot_path}.done")
    started = time.time()
    previous = {"done": 0, "total": 0}
    initial_done = None
    offset = 0
    carry = ""
    if phase == "prep":
        root, inventory = prep_inventory(source, dataset_id)
    while True:
        complete = stop.exists()
        if phase == "prep":
            sample = prep_sample(root, inventory, complete)
        else:
            try:
                with open(source) as handle:
                    handle.seek(offset)
                    text = carry + handle.read()
                    offset = handle.tell()
                sample = upload_sample(text) or previous.copy()
                carry = text[-2048:]
            except FileNotFoundError:
                sample = previous.copy()
            if complete:
                sample["done"] = max(sample["done"], sample["total"])
        sample["done"] = max(previous["done"], sample["done"])
        sample["total"] = max(sample["done"], sample["total"])
        if initial_done is None:
            initial_done = sample["done"]
        sample.update(started_at=started, updated_at=time.time(), initial_done=initial_done, complete=complete)
        write_snapshot(path, sample)
        previous = sample
        if complete:
            stop.unlink(missing_ok=True)
            return
        time.sleep(2)


if __name__ == "__main__":
    try:
        report(*sys.argv[1:])
    except Exception:
        print("Deposition progress reporting unavailable; continuing the job.", file=sys.stderr)
