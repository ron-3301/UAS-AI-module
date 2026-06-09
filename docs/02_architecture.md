# DOCUMENT 2: SYSTEM ARCHITECTURE – DETAILED LAYER DESIGN

## 1. Inter‑Layer Communication Contract

All layers communicate via **ZeroMQ (PUB‑SUB + REQ‑REP)** and **shared memory** for large data (images).  

| Data Flow                                    | Protocol          | Socket / Topic               | Data Format                                                    |
|----------------------------------------------|-------------------|------------------------------|----------------------------------------------------------------|
| Raw frame + telemetry → Layer 1              | ZeroMQ PUSH‑PULL  | tcp://*:5501                 | Multipart: [frame_id, timestamp, jpeg‑image, telemetry JSON]   |
| Pre‑processed frame → Layer 2                | Shared memory (shm)| /dev/shm/frame_{id}          | Raw BGR numpy array (640×640×3)                                |
| Detection list → Layer 3                     | ZeroMQ PUB‑SUB    | tcp://*:5502                 | JSON array of crops (base64 thumbnails)                        |
| Classification results → Layer 4             | ZeroMQ PUB‑SUB    | tcp://*:5503                 | JSON (detection_id, class, conf, threat)                       |
| Geolocated target → Layer 5                  | ZeroMQ PUB‑SUB    | tcp://*:5504                 | Full JSON targeting packet                                      |

## 2. Layer‑by‑Layer File Responsibilities (No Code – Just Purpose)

### Layer 1 – Ingestion & Pre‑processing
- `src/ingestion/frame_capture.py` – Open RTSP/camera, read frames at native FPS, publish to ZMQ.
- `src/ingestion/telemetry_parser.py` – Parse MAVLink UDP, maintain telemetry buffer.
- `src/ingestion/sync.py` – Match frame timestamps to telemetry, produce FramePacket.

### Layer 2 – Detection Engine
- `src/detection/yolo_wrapper.py` – Load TensorRT engine, run inference, return detections.
- `src/detection/nms.py` – Class‑agnostic NMS (IoU=0.45), CUDA accelerated if possible.
- `src/detection/tracker.py` – ByteTrack wrapper; assign persistent track IDs.

### Layer 3 – Identification Classifier
- `src/identification/crop_extractor.py` – Crop, pad, resize each detection to 224×224.
- `src/identification/classifier.py` – EfficientNet‑B3 ONNX inference, return top‑3 labels.
- `src/identification/threat_scorer.py` – Compute threat_score = class_weight × detection_conf × id_conf × proximity_factor.

### Layer 4 – Geolocation Engine
- `src/geolocation/raycaster.py` – Pinhole ray‑casting to terrain plane (flat or DTED).
- `src/geolocation/kalman_tracker.py` – Per‑track Kalman filter (position, velocity).
- `src/geolocation/coord_converter.py` – WGS‑84 ↔ UTM ↔ MGRS conversions (pyproj).

### Layer 5 – Output Layer
- `src/output/json_serializer.py` – Build JSON packet, send to UDP socket + MQTT.
- `src/output/video_annotator.py` – Draw boxes/labels/coordinates, stream via RTSP (GStreamer).
- `src/output/sqlite_logger.py` – Write every detection to SQLite, export KML.

## 3. Error Handling & Fallback Per Layer

| Layer | Failure                     | Fallback                                           |
|-------|-----------------------------|----------------------------------------------------|
| 1     | Camera stream drops         | Retry 3x, then output empty packets with error_code |
| 2     | GPU OOM                     | Fallback to CPU inference (slower but functional)  |
| 3     | Classifier model not found  | Use detection class only; id_confidence=0          |
| 4     | GPS loss                    | Use visual odometry from frame‑to‑frame homography  |
| 5     | MQTT broker down            | Buffer last 100 packets to disk; retry every 10s   |