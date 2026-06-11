# DOCUMENT 3: PROJECT DIRECTORY & FILE PURPOSE (Complete)

Every file in the repository has a single, clear responsibility.
uas-ai-module/
├── configs/
│ ├── inference.yaml # Runtime switches (model paths, thresholds, ports)
│ ├── training.yaml # Hyperparameters, augmentation flags, dataset splits
│ ├── cam01_intrinsics.yaml # Camera matrix, distortion coefficients, resolution
│ ├── class_weights.yaml # Threat score weights per detection class
│ └── mosquitto.conf # MQTT broker authentication & ACLs
├── data/ (DVC‑tracked)
│ ├── raw/ # Original downloaded datasets (DOTA, VEDAI, etc.) – never modified
│ ├── processed/ # YOLO‑formatted datasets, versioned (v1.0, v1.1, …)
│ ├── synthetic/ # AirSim output: images + auto‑labels in YOLO format
│ └── annotations/ # Label Studio exports, annotation SOP checklists
├── models/
│ ├── weights/ # Final model files: yolov8m_uas_v1.pt, efficientnet_b3_id_v1.onnx
│ ├── checkpoints/ # Training checkpoints (every 10 epochs) – for resuming
│ └── exports/ # TensorRT engine files: yolov8m_uas_v1.engine, classifier.engine
├── src/
│ ├── ingestion/ (frame_capture.py, telemetry_parser.py, sync.py)
│ ├── detection/ (yolo_wrapper.py, nms.py, tracker.py)
│ ├── identification/ (crop_extractor.py, classifier.py, threat_scorer.py)
│ ├── geolocation/ (raycaster.py, kalman_tracker.py, coord_converter.py)
│ ├── output/ (json_serializer.py, video_annotator.py, sqlite_logger.py)
│ ├── pipeline.py # Master orchestrator: wires all layers together
│ └── cli.py # Command‑line entry point
├── training/
│ ├── train_detector.py # Ultralytics YOLO training script
│ ├── train_classifier.py # PyTorch training for EfficientNet
│ ├── hyperparam_search.py # Optuna study launcher
│ └── eval.py # Compute mAP, confusion matrix, export plots
├── tests/
│ ├── unit/ # test_ingestion.py, test_geolocation.py, etc.
│ ├── integration/ # test_full_pipeline.py (with mocked telemetry)
│ └── fixtures/ # Sample frames, telemetry logs, expected outputs
├── scripts/
│ ├── calibrate_camera.py # Run once with checkerboard; outputs intrinsics.yaml
│ ├── dataset_stats.py # Class distribution, box size histogram, missing annotations
│ ├── benchmark_latency.py # Measure end‑to‑end latency on Jetson, output CSV
│ └── export_kml.py # Convert SQLite log to Google Earth KML
├── docs/ (all these design documents + API reference)
├── notebooks/ # For exploratory data analysis only
├── .github/workflows/
│ ├── ci.yml # Run unit tests on every push
│ └── benchmark.yml # Nightly benchmark on Jetson (if connected)
├── Dockerfile # Multi‑stage: builder + runtime
├── docker-compose.yml # For local dev: AI module + Label Studio + MQTT broker
├── requirements.txt # Pinned Python deps (torch, ultralytics, opencv, etc.)
├── .dvc/ # DVC config, cache location
└── DECISIONS.md # Decision log template