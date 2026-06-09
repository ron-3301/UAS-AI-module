# uas-ai-module

On-board AI payload for UAS. Detects, identifies, geolocates and threat-scores
ground objects from the drone's camera + MAVLink telemetry, then emits JSON
targeting recommendations to the ground station.

Targets the NVIDIA Jetson Orin NX at ~110 ms p95 latency end-to-end.

Pipeline (5 layers):

1. detection - YOLOv8m
2. identification - EfficientNet-B3 (ONNX) on cropped detections
3. geolocation - pinhole ray-cast to terrain + per-track Kalman
4. threat scoring - per docs/11
5. output - JSON-over-UDP + annotated RTSP + SQLite mission log

The downstream ground station / weapon system keeps all final authority -
this module emits *recommendations*, see `docs/12_safety_ethics_roe.md`.

## layout

see `docs/03_directory_purposes.md`.

## docs (read in order)

| # | file | what it answers |
|---|------|-----------------|
| 01 | problem_context | what missions do we support? |
| 02 | architecture | how are the 5 layers wired? |
| 03 | directory_purposes | where does each file live? |
| 04 | pipeline_dvc_active_learning | how does data flow / version? |
| 05 | phases | what do we build, in what order? |
| 06 | config_management | how are configs validated + overridden? |
| 07 | testing_strategy | what's the Go/No-Go set? |
| 08 | api_contract | what do integrators wire to us? |
| 09 | jetson_deployment | how do we ship + run on the edge? |
| 10 | decision_log_governance | how do we record *why*? |
| 11 | class_taxonomy_and_threat_model | what do we detect, how is "threat" computed? |
| 12 | safety_ethics_roe | what does the system refuse to do? |
| 13 | data_schemas | concrete shapes for the "see schema" refs |
| 14 | latency_power_budget | per-stage timing + Jetson power modes |
| 15 | annotation_sop | how are labels produced + QC'd |

## quick start (host dev)

```bash
docker compose up -d           # AI module + Label Studio + Mosquitto
python -m src.cli --config configs/inference.yaml
```

## project status

Phase 1 closed (see `docs/PHASE1_ACCEPTANCE.md` + DEC-006).

| phase | status | notes |
|-------|--------|-------|
| 1 - Foundations (W1-W2)             | done       | items 1-14 verified by `make verify-phase1`. item 15 (baseline mAP) needs GPU + DOTA. |
| 2 - Data (W3-W5)                    | in flight  | CI gates pass (`make verify-phase2`). ext-data items in `docs/PHASE2_ACCEPTANCE.md`. |
| 3 - Detection (W6-W9)               | in flight  | CI gates pass (`make verify-phase3`). end-to-end pipeline runs on synthetic frames. GPU items in `docs/PHASE3_ACCEPTANCE.md`. |
| 4 - Identification + Geolocation    | todo       |   |
| 5 - Edge Optimisation (W13-W14)     | todo       |   |
| 6 - Testing + Docs (W15-W16)        | todo       |   |

reproduce Phase-1 acceptance:

```bash
make install
make verify-phase1
```

`DECISIONS.md` is the live record of *why* things are the way they are.
