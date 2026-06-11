# DOCUMENT 14: LATENCY & POWER/THERMAL BUDGET

> Doc 1 specifies <80–150 ms end-to-end depending on scenario, and Doc 7 sets a Go/No-Go at 110 ms p95. Neither document allocates that budget across the 5 layers, nor states the power/thermal envelope. This document does both.

## 1. End-to-End Latency Budget (target: ≤ 100 ms median, ≤ 110 ms p95 on Jetson Orin NX 16 GB, 25 W mode)

| # | Stage                                          | Budget (ms) | Measured target (ms) | Notes                                              |
|---|------------------------------------------------|-------------|----------------------|----------------------------------------------------|
| 1 | Frame capture + decode (h.264 → BGR)          | 12          | 8–14                 | NVDEC hardware path; CPU path is 25+ ms (avoid)    |
| 2 | Pre-processing (resize 1920x1080 → 640x640, normalise) | 4    | 3–5                  | CUDA NPP if available                              |
| 3 | Detector inference (YOLOv8m INT8, 640²)       | 45          | 38–50                | TensorRT engine, batch=1                           |
| 4 | NMS + tracker update (ByteTrack)               | 5           | 3–7                  | CPU is fine for ≤ 50 detections                    |
| 5 | Crop + classifier inference (top-K crops, K≤8)| 15          | 8–18                 | Batched EfficientNet-B3 INT8                       |
| 6 | Geolocation (ray-cast + Kalman update)         | 3           | 1–4                  | Pure CPU, negligible                               |
| 7 | Serialisation + UDP send + SQLite insert       | 4           | 2–6                  | SQLite WAL, async commit                           |
|   | **Total**                                      | **88**      | ~70–104              | Leaves 12 ms headroom for jitter                   |

**Budget breach policy:**
- If p95 exceeds 110 ms for > 30 s, the pipeline auto-downscales detector input from 640 → 480 and logs the event (`ThermalOrLoadDegradation`).
- If p95 still > 110 ms after downscale, drop classifier (Layer 3) for one frame in two (`classifier_decimation=2`).
- These two steps are tracked as `degradation_level ∈ {0,1,2}` in the `/health` endpoint.

## 2. Per-Scenario Latency Profile

| Scenario              | Target p95 | Achieved by                                              |
|-----------------------|------------|----------------------------------------------------------|
| Wide-area (Doc 1)     | 150 ms     | Run classifier every 3rd frame; input 640                |
| Vehicle tracking      | 100 ms     | Default profile (table §1)                               |
| Point targeting       | 80 ms      | Disable classifier; rely on detector class only          |

Profiles switch via `mission_profile: [wide_area | tracking | point_targeting]` in `inference.yaml`.

## 3. Power & Thermal Budget (Jetson Orin NX 16 GB)

| Mode               | Power (W) | CPU cores | GPU clock | Use case                                |
|--------------------|-----------|-----------|-----------|-----------------------------------------|
| `MAXN`             | ~25       | 8 @ 2 GHz | max       | Bench testing only                      |
| `25W`              | 25        | 8 @ 1.5 GHz | 918 MHz | **Default flight mode**                 |
| `15W`              | 15        | 6 @ 1.2 GHz | 612 MHz | Long-endurance / cold weather           |
| `10W`              | 10        | 4 @ 1.1 GHz | 408 MHz | Standby / pre-flight                    |

`nvpmodel -m` is set in the container entrypoint based on `inference.yaml: jetson.power_mode`.

### Thermal interlocks (read by pipeline once per second via `tegrastats`):
| Junction temp | Action                                                                 |
|---------------|------------------------------------------------------------------------|
| < 70 °C       | Normal                                                                 |
| 70–80 °C      | Log warning, raise `degradation_level` to 1                            |
| 80–90 °C      | `degradation_level=2`; reduce inference resolution to 480              |
| > 90 °C       | Suspend Layer 3 (classifier) entirely; alert via `/health.last_error`  |
| > 95 °C       | Emit critical health event; **the autopilot/operator must decide whether to abort** — the AI module does not initiate an abort itself (see Doc 12 §1) |

### Memory budget (16 GB shared)
| Consumer                          | Reserved | Notes                                     |
|-----------------------------------|----------|-------------------------------------------|
| OS + container overhead           | 2.0 GB   |                                           |
| Detector TRT engine + workspace   | 1.6 GB   |                                           |
| Classifier TRT engine + workspace | 0.6 GB   |                                           |
| Frame buffers (3× 1920×1080×3)    | 0.4 GB   | Triple-buffered between capture and infer |
| Tracker / Kalman state            | 0.1 GB   | Up to 200 active tracks                   |
| SQLite WAL + logs (resident)      | 0.5 GB   | Rotated by logrotate (Doc 9)              |
| **Headroom**                      | ~10.8 GB | Plenty; the bottleneck is GPU not RAM     |

## 4. How to Measure

`scripts/benchmark_latency.py` runs a 10 000-frame replay through the live pipeline and emits a CSV with per-stage timings + a `latency_report.html` (matplotlib percentile plot). It is the canonical input to the DECISIONS.md entry "Detector model selection".
