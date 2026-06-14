"""Output schema validation helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class OutputValidationError(ValueError):
    """Raised when an advisory packet does not match the output schema."""


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "output" / "advisory_v1_1.schema.json"


class AdvisorySchemaValidator:
    """Validate advisory packets against the versioned JSON schema."""

    def __init__(self, schema_path: str | Path = DEFAULT_SCHEMA) -> None:
        self.schema_path = Path(schema_path)
        self.schema = json.loads(self.schema_path.read_text())
        try:
            from jsonschema import Draft7Validator  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise OutputValidationError("jsonschema is required for output validation") from exc
        self.validator = Draft7Validator(self.schema)

    def validate(self, packet: dict[str, Any]) -> None:
        errors = sorted(self.validator.iter_errors(packet), key=lambda err: list(err.path))
        if errors:
            messages = []
            for error in errors:
                location = "/".join(str(part) for part in error.path) or "<root>"
                messages.append(f"{location}: {error.message}")
            raise OutputValidationError("output schema validation failed:\n- " + "\n- ".join(messages))
