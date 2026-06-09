# sqlite mission-log schema sanity check (docs/13_data_schemas.md §2).
from __future__ import annotations

from pathlib import Path

from src.output.sqlite_logger import SqliteLogger


def test_schema_created(tmp_path: Path) -> None:
    db = tmp_path / "m.sqlite"
    logger = SqliteLogger(db)
    cur = logger.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"mission", "frame", "detection"}.issubset(tables)
    logger.close()
