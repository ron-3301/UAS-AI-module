# DOCUMENT 5: BUILD PHASES – WEEKLY TASK BREAKDOWN (16 Weeks)

## Phase 1 – Foundations (W1‑W2)
- **W1:** Docker environment, repo structure, config system (YAML + validation), logging.
- **W2:** Baseline YOLOv8n training on DOTA dataset. Achieve mAP@50 > 40% (proof of pipeline).

## Phase 2 – Data (W3‑W5)
- **W3:** Download & convert all public datasets (DOTA, VEDAI, xView) → YOLO format.
- **W4:** Label internal images (500 images) + synthetic data generation (2000 images via AirSim).
- **W5:** Dataset v1.0 – 10k instances. Run `dataset_stats.py` and fix imbalances.

## Phase 3 – Detection (W6‑W9)
- **W6:** Benchmark YOLOv8s, YOLOv8m, YOLOv10, RT-DETR. Select best mAP/latency trade‑off.
- **W7:** Hyperparameter optimisation (Optuna, 50 trials).
- **W8:** Full training (300 epochs) → evaluate on test set.
- **W9:** Error analysis → collect 500 more hard negatives → retrain → reach 80% mAP.

## Phase 4 – Identification & Geolocation (W10‑W12)
- **W10:** Train EfficientNet‑B3 on cropped detections (fine‑grained sub‑classes).
- **W11:** Implement ray‑casting geolocation (flat earth first). Unit test against simulated camera.
- **W12:** Integrate Kalman filter tracker, measure CEP on synthetic flight (AirSim).

## Phase 5 – Edge Optimisation (W13‑W14)
- **W13:** INT8 post‑training quantisation, export to TensorRT. Validate <2% mAP drop.
- **W14:** Deploy to Jetson Orin. Profile latency, memory, power. Fix I/O bottlenecks.

## Phase 6 – Testing & Documentation (W15‑W16)
- **W15:** Write unit/integration tests → achieve >85% coverage.
- **W16:** Adversarial testing (camouflage, occlusion, low light). Produce final benchmark report.

**Critical path:** Data → Detection → Geolocation → Edge. Do not start Phase 3 without Phase 2 dataset.