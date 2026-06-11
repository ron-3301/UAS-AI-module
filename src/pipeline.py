from typing import Dict, Any
import numpy as np
from src.ingestion.frame_capture import FrameCapture
from src.ingestion.telemetry_parser import TelemetryParser
from src.detection.yolo_wrapper import MockDetector
from src.identification.crop_extractor import extract_crops
from src.identification.classifier import MockClassifier
from src.identification.threat_scorer import compute_threat
from src.geolocation.raycaster import estimate_geolocation
from src.output.json_serializer import serialize

class Pipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.capture = FrameCapture("mock")
        self.telemetry = TelemetryParser()
        self.detector = MockDetector(config["detection"]["conf_threshold"])
        self.classifier = MockClassifier()
        self.mission_id = config["mission_id"]

    def process_frame(self, frame: np.ndarray = None) -> Dict[str, Any]:
        if frame is None:
            frame = self.capture.read()
        telemetry = self.telemetry.parse({})
        dets = self.detector.predict(frame)
        dets = self.detector.update(dets)
        crops = extract_crops(frame, dets)
        id_results = self.classifier.predict(crops)
        threat_scores = [compute_threat(d, idr) for d, idr in zip(dets, id_results)]
        geo_results = [estimate_geolocation(d, telemetry, {}) for d in dets]
        packet = serialize(
            self.mission_id,
            getattr(self.capture, "frame_id", 1),
            telemetry,
            dets,
            id_results,
            geo_results,
            threat_scores
        )
        return packet
