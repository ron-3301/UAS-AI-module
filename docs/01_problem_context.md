# DOCUMENT 1: PROBLEM STATEMENT & PROJECT CONTEXT (Expanded)

## 1. Operational Scenarios

Define three concrete mission types that drive design decisions:

| Scenario               | Altitude        | Target Size (px) | Required Latency | Geolocation Priority |
|------------------------|----------------|------------------|------------------|----------------------|
| Wide‑area surveillance | 200–500 m AGL   | 10–30 px         | <150 ms          | Low (detection only) |
| Vehicle tracking       | 80–150 m AGL    | 30–80 px         | <100 ms          | High (tracking)      |
| Point targeting        | 50–100 m AGL    | 80–200 px        | <80 ms           | Critical (<5m CEP)   |

## 2. Failure Modes & Graceful Degradation

- **Loss of GPS** → fallback to visual odometry + relative bearing output.
- **Camera occlusion (smoke, cloud)** → output last known coordinates with `validity_flag=false`.
- **Model confidence < threshold** → suppress detection but still output telemetry packet with `detections=[]`.
- **Jetson thermal throttling** → reduce inference resolution from 1280 to 640 automatically (configurable).

## 3. Stakeholder Assumptions (to be made explicit)

- The UAS flight controller provides MAVLink 2.0 telemetry at minimum 10 Hz.
- Sensor calibration file (camera matrix + distortion) is provided before first flight.
- No internet connectivity during mission – all models must run onboard.
- Downstream weapon system has its own safety interlocks; this module outputs *targeting recommendations* only.

## 4. Required Inputs / Outputs (Hard Contract)

| Input                        | Format                           | Source                     |
|------------------------------|----------------------------------|----------------------------|
| Video stream                 | RTSP, UDP h.264, or USB/MIPI     | UAS camera payload         |
| Telemetry                    | MAVLink 2.0 (UDP port 14550)     | Flight controller / autopilot |
| Camera calibration file      | YAML (fx, fy, cx, cy, distortion)| Provided by integrator     |

| Output                       | Format                           | Destination                |
|------------------------------|----------------------------------|----------------------------|
| Targeting packet             | JSON over UDP (port 5005)        | Ground station / weapon system |
| Annotated video stream       | RTSP (port 8554)                 | Operator monitor           |
| Mission log                  | SQLite file                      | Onboard storage            |
| Health / metrics             | HTTP /health (port 8080)         | Ground control             |