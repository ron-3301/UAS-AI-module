# DOCUMENT 6: CONFIGURATION MANAGEMENT & VALIDATION

## 1. Config Schema (JSON Schema for Validation)

Each YAML file is validated against a JSON schema at startup using `jsonschema` (Python).  
Example schema for `inference.yaml`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "model": {
      "type": "object",
      "properties": {
        "detection_weights": {"type": "string", "pattern": "\\.(pt|engine)$"},
        "detection_conf_threshold": {"type": "number", "minimum": 0.1, "maximum": 0.99}
      },
      "required": ["detection_weights", "detection_conf_threshold"]
    },
    "output": {
      "type": "object",
      "properties": {
        "json_socket_port": {"type": "integer", "minimum": 1024, "maximum": 65535}
      }
    }
  }
}
2. Environment Override
Priority (highest to lowest):

Command‑line flag (--config and --override key=value)

Environment variable (e.g., UAS_CONF_THRESH=0.6)

YAML file value

Built‑in default

Set UAS_ENV=production to automatically switch to production‑optimised config paths.

3. Configuration Versioning
All config files have a mandatory version field (e.g., version: "1.0").
The pipeline code checks major.minor compatibility. Mismatch → warning but continues.
Breaking changes (e.g., renamed field) require a major version bump and will cause an error exit.

4. Example Config Skeleton (inference.yaml)
yaml
version: "1.0"
model:
  detection_weights: models/weights/yolov8m_uas_v1.engine
  detection_input_size: 640
  detection_conf_threshold: 0.45
  classifier_weights: models/weights/efficientnet_b3_id_v1.onnx
sensor:
  modality: EO
  calibration_file: configs/cam01_intrinsics.yaml
telemetry:
  source: mavlink
  udp_port: 14550
geolocation:
  terrain_model: flat_earth
output:
  json_socket_port: 5005
  mqtt_broker: 192.168.1.1