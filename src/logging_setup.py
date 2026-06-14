from __future__ import annotations

# loguru sink wiring. used by src.cli and every training script entry.


import sys
from pathlib import Path

from loguru import logger

_FMT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "| <level>{level:<7}</level> "
    "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "- <level>{message}</level>"
)


def configure(level: str = "INFO", log_dir: str | Path | None = None) -> None:
    # safe to call more than once - clears sinks first
    logger.remove()
    logger.add(sys.stderr, level=level, format=_FMT, colorize=True)
    if not log_dir:
        return
    p = Path(log_dir)
    p.mkdir(parents=True, exist_ok=True)
    logger.add(
        p / "uas.log",
        level="DEBUG",
        rotation="100 MB",
        retention=7,
        compression="zip",
        enqueue=True,           # multi-proc safe
        backtrace=True,
        diagnose=False,         # don't leak locals/secrets in tracebacks
    )
