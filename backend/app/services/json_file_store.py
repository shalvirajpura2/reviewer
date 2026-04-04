import json
import os
from pathlib import Path


def read_json_object(path: Path, fallback: dict[str, object]) -> dict[str, object]:
    if not path.exists():
        return dict(fallback)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(fallback)

    if not isinstance(payload, dict):
        return dict(fallback)

    merged_payload = dict(fallback)
    merged_payload.update(payload)
    return merged_payload


def write_json_object(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")

    with temp_path.open("w", encoding="utf-8") as temp_file:
        json.dump(payload, temp_file, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())

    os.replace(temp_path, path)