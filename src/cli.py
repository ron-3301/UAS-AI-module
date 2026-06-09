# CLI entry. usage:
#   python -m src.cli --config configs/inference.yaml [--dry-run]
from __future__ import annotations

import argparse
from pathlib import Path

from loguru import logger

from src.config import load_and_validate
from src.logging_setup import configure as configure_logging
from src.pipeline import Pipeline


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="uas-ai", description=__doc__)
    p.add_argument("--config", type=Path, required=True, help="Path to inference.yaml")
    p.add_argument(
        "--override", action="append", default=[], metavar="KEY=VALUE",
        help="Override a config key (highest precedence). Repeatable.",
    )
    p.add_argument("--dry-run", action="store_true", help="Validate config & exit")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cfg = load_and_validate(args.config, overrides=args.override)
    configure_logging(level=cfg["log_level"], log_dir=cfg["log_dir"])

    if args.dry_run:
        logger.info("Config OK: {}", args.config)
        return 0

    # TODO: real wiring (frame_source, detector, classifier, geolocator, emitter)
    # lands when we run on the Jetson. Until then this raises by design.
    pipe = Pipeline(cfg)
    try:
        pipe.run()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
    finally:
        pipe.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
