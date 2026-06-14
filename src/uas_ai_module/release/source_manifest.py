"""Source release manifest generation."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_EXCLUDE_PARTS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    ".venv",
    "venv",
}


@dataclass(frozen=True)
class SourceFileEntry:
    path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceManifest:
    version: str
    file_count: int
    files: tuple[SourceFileEntry, ...]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "file_count": self.file_count,
            "files": [asdict(item) for item in self.files],
        }


def build_source_manifest(root: str | Path, *, version: str = "1.0") -> SourceManifest:
    root_path = Path(root).resolve()
    entries: list[SourceFileEntry] = []
    for path in sorted(root_path.rglob("*")):
        if not path.is_file() or _is_excluded(path, root_path):
            continue
        relative = path.relative_to(root_path).as_posix()
        entries.append(SourceFileEntry(relative, path.stat().st_size, sha256_file(path)))
    return SourceManifest(version=version, file_count=len(entries), files=tuple(entries))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_excluded(path: Path, root: Path) -> bool:
    parts = set(path.relative_to(root).parts)
    return bool(parts & DEFAULT_EXCLUDE_PARTS)
