"""Apply frozen wizard metadata after sync, before validating the generated Portal YAML."""

from pathlib import Path

import yaml


def apply_metadata(path, metadata):
    path = Path(path)
    config = yaml.safe_load(path.read_text())
    datasets = config.get("datasets") if isinstance(config, dict) else None
    if not isinstance(datasets, list) or len(datasets) != 1:
        raise ValueError("Expected exactly one dataset in the generated Portal YAML")
    current = datasets[0].get("metadata")
    if not isinstance(current, dict) or current.get("dataset_identifier") != metadata.get("dataset_identifier"):
        raise ValueError("Generated Portal YAML does not match the prepared dataset")
    for key, value in metadata.items():
        if value is None:
            current.pop(key, None)
        else:
            current[key] = value

    # Overwrite in place; truncation keeps the file's group access from sync.
    path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
