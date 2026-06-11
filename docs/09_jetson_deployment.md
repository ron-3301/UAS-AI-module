## Document 9: `9_jetson_deployment.md`

```markdown
# DOCUMENT 9: DEPLOYMENT TO JETSON (Step‑by‑Step Without Code)

## 1. Prerequisites

- Jetson Orin NX with JetPack 6.0 (or newer) flashed.
- 64GB microSD card (or NVMe) for dataset/model storage.
- Camera (CSI or USB) connected and tested with `v4l2-ctl --list-devices`.
- Docker with NVIDIA Container Toolkit installed on Jetson.

## 2. Build Process on Host (x86) for Cross‑Platform

1. Build Docker image with `--platform=linux/arm64` using QEMU or a Jetson native builder.
2. Do **not** export TensorRT engine on host – engine is architecture‑specific.
3. Copy the ONNX model to Jetson and build engine on the Jetson itself using `trtexec`.

## 3. On‑Jetson Steps (Command Examples – for understanding)

- Pull Docker image:  
  `docker pull your-registry/uas-ai:jetpack6`

- Run container with GPU access, camera, serial:  
docker run --runtime=nvidia
--device /dev/video0
--device /dev/ttyUSB0
-v /path/to/models:/workspace/models
-v /path/to/logs:/workspace/logs
-p 5005:5005 -p 8554:8554 -p 8080:8080
uas-ai:jetpack6

text

- First‑time calibration:  
`python scripts/calibrate_camera.py --checkerboard 9x6 --output configs/cam_intrinsics.yaml`

- Start pipeline:  
`python cli.py --config configs/inference_jetson.yaml`

## 4. Monitoring & Log Rotation

- Logs written to `logs/` inside container – mount a host directory.
- On host, configure `logrotate` to rotate files every 100MB or daily.
- Use `docker stats` or `tegrastats` to monitor Jetson resources.

## 5. Production Optimisations

- Use `--network=host` for lowest latency ZeroMQ/RTSP.
- Disable debug logs (`log_level: WARNING` in config).
- Set CPU governor to `performance`.
- Pin inference threads to specific cores via `taskset`.