"""External SITL/hardware validation plan parsing.

The plan describes checks that may require external resources. It does not run
vehicle commands; it only describes read-only smoke checks for telemetry, camera,
model artifacts, TensorRT boundaries, and observability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ExternalValidationPlanError(ValueError):
    """Raised when an external validation plan is invalid."""


@dataclass(frozen=True)
class ExternalCheck:
    name: str
    kind: str
    enabled: bool
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ExternalValidationPlan:
    version: str
    plan_id: str
    advisory_only: bool
    checks: tuple[ExternalCheck, ...]

    def enabled_checks(self) -> tuple[ExternalCheck, ...]:
        return tuple(check for check in self.checks if check.enabled)


def load_external_validation_plan(path: str | Path) -> ExternalValidationPlan:
    plan_path = Path(path)
    data = json.loads(plan_path.read_text())
    if not isinstance(data, dict):
        raise ExternalValidationPlanError("external validation plan root must be an object")
    advisory_only = bool(data.get("advisory_only", False))
    if advisory_only is not True:
        raise ExternalValidationPlanError("external validation plan must set advisory_only=true")
    checks_raw = data.get("checks")
    if not isinstance(checks_raw, list) or not checks_raw:
        raise ExternalValidationPlanError("external validation plan must contain non-empty checks list")
    checks = tuple(_parse_check(item, idx) for idx, item in enumerate(checks_raw))
    return ExternalValidationPlan(
        version=str(data.get("version", "0.0")),
        plan_id=str(data.get("plan_id", "external-validation")),
        advisory_only=advisory_only,
        checks=checks,
    )


def _parse_check(item: Any, idx: int) -> ExternalCheck:
    if not isinstance(item, dict):
        raise ExternalValidationPlanError(f"check {idx} must be an object")
    name = str(item.get("name", f"check-{idx}"))
    kind = str(item.get("kind", ""))
    if kind not in {"mavlink", "camera", "onnx", "tensorrt", "observability"}:
        raise ExternalValidationPlanError(f"check {name!r} has unsupported kind {kind!r}")
    parameters = item.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ExternalValidationPlanError(f"check {name!r} parameters must be an object")
    return ExternalCheck(name=name, kind=kind, enabled=bool(item.get("enabled", True)), parameters=parameters)
