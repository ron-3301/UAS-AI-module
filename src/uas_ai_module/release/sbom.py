"""Minimal requirements-based SBOM helpers."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RequirementEntry:
    name: str
    specifier: str | None
    marker: str | None
    source_file: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_requirements_file(path: str | Path) -> tuple[RequirementEntry, ...]:
    req_path = Path(path)
    entries: list[RequirementEntry] = []
    for raw_line in req_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        marker = None
        if ";" in line:
            line, marker = [part.strip() for part in line.split(";", 1)]
        match = re.match(r"([A-Za-z0-9_.-]+)(.*)", line)
        if not match:
            continue
        name = match.group(1).lower().replace("_", "-")
        specifier = match.group(2).strip() or None
        entries.append(RequirementEntry(name=name, specifier=specifier, marker=marker, source_file=req_path.as_posix()))
    return tuple(entries)
