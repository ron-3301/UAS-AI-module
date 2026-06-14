from __future__ import annotations

# layer 5 - write every detection (kept AND suppressed) to sqlite.
# schema lives in docs/13 §2.


import sqlite3
from pathlib import Path

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS mission (
  mission_id        TEXT PRIMARY KEY,
  start_utc         TEXT NOT NULL,
  end_utc           TEXT,
  detector_sha      TEXT,
  classifier_sha    TEXT,
  dataset_version   TEXT,
  config_sha        TEXT,
  ruleset_version   TEXT,
  notes             TEXT
);
CREATE TABLE IF NOT EXISTS frame (
  frame_id          INTEGER PRIMARY KEY,
  timestamp_utc     TEXT NOT NULL,
  lat               REAL, lon REAL,
  alt_msl_m         REAL, alt_agl_m REAL,
  roll_deg          REAL, pitch_deg REAL, yaw_deg REAL,
  fps_inst          REAL
);
CREATE TABLE IF NOT EXISTS detection (
  detection_id      TEXT PRIMARY KEY,
  frame_id          INTEGER REFERENCES frame(frame_id),
  track_id          INTEGER,
  bbox_x            INTEGER, bbox_y INTEGER, bbox_w INTEGER, bbox_h INTEGER,
  detection_class   TEXT NOT NULL,
  detection_conf    REAL NOT NULL,
  id_label          TEXT,
  id_conf           REAL,
  threat_score      REAL,
  geo_lat           REAL, geo_lon REAL, cep_m REAL,
  validity_flag     INTEGER NOT NULL DEFAULT 1,
  suppression_reason TEXT,
  raw_packet_json   TEXT
);
CREATE INDEX IF NOT EXISTS idx_det_frame ON detection(frame_id);
CREATE INDEX IF NOT EXISTS idx_det_track ON detection(track_id);
CREATE INDEX IF NOT EXISTS idx_det_class ON detection(detection_class);
"""


class SqliteLogger:
    def __init__(self, db_path: str | Path) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # autocommit so each insert hits disk; WAL mode keeps it cheap
        self.conn = sqlite3.connect(str(db_path), isolation_level=None)
        self.conn.executescript(_SCHEMA)

    def close(self) -> None:
        self.conn.close()
