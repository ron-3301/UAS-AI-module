# DOCUMENT 13: DATA SCHEMAS — CAMERA, SQLITE, MQTT, TIME-SYNC, VISUAL ODOMETRY

> Fills gaps left by Docs 2, 6, and 8: schemas that are *referenced* but never *defined*.

---

## 1. Camera Intrinsics YAML (`configs/cam01_intrinsics.yaml`)

```yaml
version: "1.0"
camera_id: cam01
make_model: "Sony IMX477 + 6mm M12 lens"
resolution: { width: 1920, height: 1080 }
# Pinhole intrinsics (pixels)
fx: 1462.3
fy: 1461.8
cx: 960.1
cy: 540.4
# Plumb-bob / Brown distortion coefficients
distortion_model: plumb_bob   # [plumb_bob | equidistant | none]
distortion: { k1: -0.281, k2:  0.108, p1: 0.0004, p2: -0.0009, k3: 0.0 }
# Mounting (camera frame -> body frame), right-hand, +X forward, +Y right, +Z down
mount:
  translation_m: { x: 0.10, y: 0.00, z: -0.05 }   # camera 10 cm fwd, 5 cm above body origin
  rotation_deg:  { roll: 0.0, pitch: -90.0, yaw: 0.0 }  # nadir-down
# Calibration provenance
calibrated_on: "2026-05-22"
calibrated_by: "scripts/calibrate_camera.py"
reprojection_error_px: 0.41
```

JSON-Schema fragment (added to the validator in Doc 6):

```json
{
  "type":"object","required":["version","fx","fy","cx","cy","mount"],
  "properties":{
    "fx":{"type":"number","minimum":1},
    "fy":{"type":"number","minimum":1},
    "cx":{"type":"number"},"cy":{"type":"number"},
    "distortion_model":{"enum":["plumb_bob","equidistant","none"]},
    "mount":{"type":"object","required":["translation_m","rotation_deg"]}
  }
}
```

---

## 2. SQLite Mission-Log Schema

File path: `logs/missions/MSN-YYYYMMDD-NNN.sqlite`. Created at pipeline start, never truncated mid-mission.

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE mission (
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

CREATE TABLE frame (
  frame_id          INTEGER PRIMARY KEY,
  timestamp_utc     TEXT NOT NULL,
  lat               REAL, lon REAL,
  alt_msl_m         REAL, alt_agl_m REAL,
  roll_deg          REAL, pitch_deg REAL, yaw_deg REAL,
  fps_inst          REAL
);

CREATE TABLE detection (
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
  validity_flag     INTEGER NOT NULL DEFAULT 1,   -- 0/1
  suppression_reason TEXT,                         -- NULL if emitted
  raw_packet_json   TEXT                           -- full outbound JSON for audit
);

CREATE INDEX idx_det_frame   ON detection(frame_id);
CREATE INDEX idx_det_track   ON detection(track_id);
CREATE INDEX idx_det_class   ON detection(detection_class);
```

`scripts/export_kml.py` reads `detection` joined to `frame` and emits a Google-Earth KML colour-coded by `threat_score`.

---

## 3. MQTT Topic Structure

Used as a secondary publication channel in addition to UDP (Doc 2 Layer 5).

| Topic                                            | Payload                  | QoS | Retain |
|--------------------------------------------------|--------------------------|-----|--------|
| `uas/{uas_id}/targets`                           | Full targeting packet    | 1   | false  |
| `uas/{uas_id}/health`                            | Same as `/health` HTTP   | 0   | true   |
| `uas/{uas_id}/error`                             | Error packets only       | 1   | false  |
| `uas/{uas_id}/heartbeat`                         | `{ts, fps, mission_id}` @1Hz | 0 | true   |

ACLs are enforced by `configs/mosquitto.conf`:
- The AI module has **publish-only** rights on its own `uas/{uas_id}/#` subtree.
- Ground station has subscribe-only.
- No cross-UAS publish allowed (prevents a compromised module from spoofing siblings).

---

## 4. Time Synchronisation (`src/ingestion/sync.py`)

Three timestamps must be reconciled per frame:
- `t_cam`   – PTS from the GStreamer/V4L2 capture pipeline (monotonic, nanoseconds).
- `t_mav`   – `time_boot_ms` from MAVLink.
- `t_utc`   – wall-clock UTC (from Jetson clock, ideally NTP- or PPS-disciplined).

### Algorithm
1. On startup, capture `(t_cam0, t_mav0, t_utc0)` simultaneously while the camera is streaming and MAVLink is up. Store offsets:
   - `offset_cam_to_utc_ns = t_utc0 − t_cam0`
   - `offset_mav_to_utc_ms = t_utc0 − t_mav0`
2. For each frame:
   - `frame_utc = t_cam + offset_cam_to_utc_ns`
   - Search the MAVLink ring buffer (last 1 s) for the message whose `time_boot_ms + offset_mav_to_utc_ms` is closest to `frame_utc`.
   - If the closest match is > 100 ms away, mark `telemetry_stale=true` and use linear interpolation between the two nearest messages.
3. Re-estimate offsets every 30 s via Kalman smoothing to absorb clock drift.

### Acceptance
- Median frame-to-telemetry skew on the bench rig < 15 ms (verified by `tests/unit/test_sync.py` against a recorded log with injected jitter).

---

## 5. Visual-Odometry Fallback (GPS-denied mode)

Triggered when: no `GLOBAL_POSITION_INT` for > 2 s OR HDOP > 5.

Approach (simple, no SLAM):
- Compute frame-to-frame homography on FAST corners + ORB descriptors (OpenCV).
- Integrate the homography decomposed against the known camera intrinsics + the *last known* altitude AGL to estimate planar translation in body frame.
- Convert to WGS-84 by dead-reckoning from the last good GPS fix; flag every output with `geolocation.source = "vo"` and a growing CEP (`cep_m += 0.5 m per second of VO drift` as a coarse heuristic).
- Reset on the first valid GPS message.

This is intentionally a **degraded** mode — it provides a *bearing* and an *order-of-magnitude* position only. The output layer sets `validity_flag=false` after 60 s of continuous VO, per Doc 12 §5.
