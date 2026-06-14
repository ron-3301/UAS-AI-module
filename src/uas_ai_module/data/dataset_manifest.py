"""Dataset manifest parsing and validation.

This module is intentionally lightweight and runtime-safe. It does not import
training frameworks. It validates dataset governance metadata so x86-side
training/export work can be prepared reproducibly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_MANIFEST_SCHEMA = PROJECT_ROOT / "schemas" / "data" / "dataset_manifest.schema.json"


class DatasetManifestError(ValueError):
    """Raised when a dataset manifest is invalid."""


@dataclass(frozen=True)
class DatasetSplit:
    name: str
    image_dir: Path
    annotation_file: Path
    image_count: int
    class_counts: dict[str, int]


@dataclass(frozen=True)
class DatasetManifest:
    version: str
    dataset_id: str
    taxonomy_version: str
    class_names: tuple[str, ...]
    root: Path
    splits: tuple[DatasetSplit, ...]
    sources: tuple[str, ...]

    @property
    def total_images(self) -> int:
        return sum(split.image_count for split in self.splits)

    @property
    def aggregate_class_counts(self) -> dict[str, int]:
        counts = {name: 0 for name in self.class_names}
        for split in self.splits:
            for class_name, count in split.class_counts.items():
                counts[class_name] = counts.get(class_name, 0) + count
        return counts

    def split_names(self) -> tuple[str, ...]:
        return tuple(split.name for split in self.splits)


def load_dataset_manifest(path: str | Path, *, validate_files_exist: bool = False) -> DatasetManifest:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text())
    _validate_schema_if_available(data)

    class_names = tuple(str(item) for item in data["classes"])
    if len(set(class_names)) != len(class_names):
        raise DatasetManifestError("dataset classes must be unique")

    root_raw = Path(str(data["root"]))
    root = root_raw if root_raw.is_absolute() else (manifest_path.parent / root_raw).resolve()

    splits = tuple(
        _parse_split(item, root=root, class_names=class_names, validate_files_exist=validate_files_exist)
        for item in data["splits"]
    )
    split_names = [split.name for split in splits]
    if len(set(split_names)) != len(split_names):
        raise DatasetManifestError("dataset split names must be unique")

    return DatasetManifest(
        version=str(data["version"]),
        dataset_id=str(data["dataset_id"]),
        taxonomy_version=str(data["taxonomy_version"]),
        class_names=class_names,
        root=root,
        splits=splits,
        sources=tuple(str(item) for item in data.get("sources", [])),
    )


def dataset_report(manifest: DatasetManifest) -> dict[str, Any]:
    """Return a serializable dataset summary report."""

    return {
        "version": manifest.version,
        "dataset_id": manifest.dataset_id,
        "taxonomy_version": manifest.taxonomy_version,
        "total_images": manifest.total_images,
        "classes": list(manifest.class_names),
        "aggregate_class_counts": manifest.aggregate_class_counts,
        "splits": [
            {
                "name": split.name,
                "image_count": split.image_count,
                "class_counts": split.class_counts,
                "image_dir": str(split.image_dir),
                "annotation_file": str(split.annotation_file),
            }
            for split in manifest.splits
        ],
        "sources": list(manifest.sources),
    }


def class_balance_warnings(
    manifest: DatasetManifest,
    *,
    min_fraction: float = 0.01,
    max_imbalance_ratio: float = 100.0,
) -> list[str]:
    """Return class-balance warnings for aggregate class counts."""

    if min_fraction < 0 or max_imbalance_ratio <= 0:
        raise ValueError("class balance thresholds must be non-negative/positive")
    counts = manifest.aggregate_class_counts
    total = sum(counts.values())
    if total <= 0:
        return ["no annotations counted"]
    warnings: list[str] = []
    nonzero = [count for count in counts.values() if count > 0]
    if not nonzero:
        return ["all class counts are zero"]
    min_nonzero = min(nonzero)
    max_count = max(nonzero)
    if max_count / max(min_nonzero, 1) > max_imbalance_ratio:
        warnings.append(
            f"class imbalance ratio {max_count / max(min_nonzero, 1):.2f} exceeds {max_imbalance_ratio:.2f}"
        )
    for class_name, count in counts.items():
        fraction = count / total
        if fraction < min_fraction:
            warnings.append(
                f"class {class_name!r} fraction {fraction:.4f} below minimum {min_fraction:.4f}"
            )
    return warnings


def _parse_split(
    item: dict[str, Any],
    *,
    root: Path,
    class_names: tuple[str, ...],
    validate_files_exist: bool,
) -> DatasetSplit:
    name = str(item["name"])
    image_dir = root / str(item["image_dir"])
    annotation_file = root / str(item["annotation_file"])
    image_count = int(item["image_count"])
    if image_count < 0:
        raise DatasetManifestError(f"split {name!r} image_count must be non-negative")
    class_counts = {str(key): int(value) for key, value in item.get("class_counts", {}).items()}
    unknown = sorted(set(class_counts) - set(class_names))
    if unknown:
        raise DatasetManifestError(f"split {name!r} contains unknown class count keys: {unknown}")
    if any(value < 0 for value in class_counts.values()):
        raise DatasetManifestError(f"split {name!r} class counts must be non-negative")
    if validate_files_exist:
        if not image_dir.exists():
            raise DatasetManifestError(f"split {name!r} image_dir not found: {image_dir}")
        if not annotation_file.exists():
            raise DatasetManifestError(f"split {name!r} annotation_file not found: {annotation_file}")
    return DatasetSplit(name, image_dir, annotation_file, image_count, class_counts)


def _validate_schema_if_available(data: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        return
    schema = json.loads(DATASET_MANIFEST_SCHEMA.read_text())
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if errors:
        messages = []
        for error in errors:
            location = "/".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        raise DatasetManifestError("dataset manifest schema validation failed:\n- " + "\n- ".join(messages))
