#!/usr/bin/env bash
# Build TensorRT engines for detector and classifier. Run on the target Jetson.
# Reads ONNX from models/weights/, writes engines to models/exports/.
set -euo pipefail

WEIGHTS=models/weights
EXPORTS=models/exports
mkdir -p "$EXPORTS"

DET_ONNX="$WEIGHTS/yolov8m_uas_v1.onnx"
CLS_ONNX="$WEIGHTS/efficientnet_b3_id_v1.onnx"

if [[ -f "$DET_ONNX" ]]; then
  trtexec \
    --onnx="$DET_ONNX" \
    --int8 \
    --workspace=2048 \
    --saveEngine="$EXPORTS/yolov8m_uas_v1.engine"
else
  echo "WARNING: $DET_ONNX missing; skipping detector engine"
fi

if [[ -f "$CLS_ONNX" ]]; then
  trtexec \
    --onnx="$CLS_ONNX" \
    --int8 \
    --workspace=1024 \
    --saveEngine="$EXPORTS/efficientnet_b3_id_v1.engine"
else
  echo "WARNING: $CLS_ONNX missing; skipping classifier engine"
fi

echo "Done."
