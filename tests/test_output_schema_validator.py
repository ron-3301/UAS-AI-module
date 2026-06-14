from __future__ import annotations

from uas_ai_module.pipeline import Pipeline
from uas_ai_module.output.schema_validator import AdvisorySchemaValidator, OutputValidationError


def test_dry_run_packet_validates_against_output_schema() -> None:
    packet = Pipeline.dry_run("schema-test-uas").run_once().advisory
    AdvisorySchemaValidator().validate(packet)


def test_output_schema_rejects_non_advisory_packet() -> None:
    packet = Pipeline.dry_run("schema-test-uas").run_once().advisory
    packet["advisory_only"] = False
    validator = AdvisorySchemaValidator()
    try:
        validator.validate(packet)
    except OutputValidationError as exc:
        assert "advisory_only" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("schema validator accepted advisory_only=false")
