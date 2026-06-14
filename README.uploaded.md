# uas-ai-module

Complete implementation of all 12 phases with real functionality (no stubs).

## Pipeline
1. Ingestion (camera + MAVLink)
2. Detection (YOLOv8m TensorRT)
3. Identification (EfficientNet-B3 TensorRT)
4. Geolocation (pinhole + Kalman/IMM)
5. Output (JSON/UDP)

## Safety
Hard-coded filters in src/output/json_serializer.py (cannot be disabled via config).

## Status
All phases (1-12) complete with real code. TensorRT-only inference on Jetson.