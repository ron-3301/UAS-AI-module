# master pipeline orchestrator.
#
# in-process version: each layer is a callable, all run sync on one thread.
# per DEC-002, prod will wrap each layer in its own process linked over
# ZeroMQ. that wrapper goes in src.runtime when Phase 5 lands.
#
# every collaborator is injected via the ctor so the integration test can
# swap in mocks (mock detector, mock classifier, pre-recorded telemetry).
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from src.detection.nms import class_agnostic_nms
from src.detection.tracker import IouTracker
from src.identification.crop_extractor import batch_extract
from src.identification.threat_scorer import ThreatInputs, ThreatScorer
from src.output.json_serializer import (
    Detection as OutDetection,
)
from src.output.json_serializer import (
    Packet as OutPacket,
)
from src.output.json_serializer import (
    build_packet,
)
from src.types import (
    FramePacket,
    GeolocatedDetection,
    IdentifiedDetection,
    RawDetection,
    StageTiming,
)

# injected callable type aliases
Detector   = Callable[[FramePacket], list[RawDetection]]
Classifier = Callable[[list[Any]], list[tuple[str, float]]]
Geolocator = Callable[[IdentifiedDetection, FramePacket], dict[str, float] | None]
Emitter    = Callable[[dict[str, Any]], None]


@dataclass
class PipelineMetrics:
    n_frames: int = 0
    n_detections_raw: int = 0
    n_detections_emitted: int = 0
    n_suppressed: int = 0
    cumulative_stage_ms: dict[str, float] = field(default_factory=dict)

    def absorb(self, timing: StageTiming) -> None:
        for s, ms in timing.stages.items():
            self.cumulative_stage_ms[s] = self.cumulative_stage_ms.get(s, 0.0) + ms

    @property
    def mean_stage_ms(self) -> dict[str, float]:
        if self.n_frames == 0:
            return {k: 0.0 for k in self.cumulative_stage_ms}
        return {k: v / self.n_frames for k, v in self.cumulative_stage_ms.items()}


class Pipeline:
    # runs the 5-layer pipeline. sync, single-threaded, fully testable.
    def __init__(
        self,
        *,
        cfg: dict[str, Any],
        frame_source: Iterator[FramePacket],
        detector: Detector,
        classifier: Classifier | None = None,
        geolocator: Geolocator | None = None,
        emitter: Emitter | None = None,
        threat_scorer: ThreatScorer | None = None,
        tracker: IouTracker | None = None,
    ) -> None:
        self.cfg = cfg
        self.frame_source = frame_source
        self.detector = detector
        self.classifier = classifier
        self.geolocator = geolocator
        self.emitter = emitter or (lambda _: None)
        self.tracker = tracker or IouTracker()
        self.threat_scorer = threat_scorer
        self.metrics = PipelineMetrics()

        model_cfg = cfg.get("model", {})
        self._iou_threshold = float(model_cfg.get("detection_iou_threshold", 0.45))
        self._classifier_input_size = int(model_cfg.get("classifier_input_size", 224))
        self._mission_id = cfg.get("mission_id", "MSN-DEV-LOCAL")

    def run(self, max_frames: int | None = None) -> PipelineMetrics:
        for pkt in self.frame_source:
            self.metrics.n_frames += 1
            timing = StageTiming()

            # --- detect ---
            t0 = time.perf_counter()
            raw = self.detector(pkt)
            timing.add("detect", (time.perf_counter() - t0) * 1000.0)
            self.metrics.n_detections_raw += len(raw)

            # --- nms + track ---
            t0 = time.perf_counter()
            raw = class_agnostic_nms(raw, iou_threshold=self._iou_threshold)
            raw = self.tracker.update(pkt.frame_id, raw)
            timing.add("nms_track", (time.perf_counter() - t0) * 1000.0)

            # --- identify (+ score) ---
            t0 = time.perf_counter()
            ided = self._identify(pkt, raw)
            timing.add("identify", (time.perf_counter() - t0) * 1000.0)

            # --- geolocate ---
            t0 = time.perf_counter()
            geo = [self._geolocate(i, pkt) for i in ided]
            timing.add("geolocate", (time.perf_counter() - t0) * 1000.0)

            # --- serialise + safety filter ---
            t0 = time.perf_counter()
            out, suppressed = self._serialise(pkt, geo)
            timing.add("serialise", (time.perf_counter() - t0) * 1000.0)

            self.metrics.n_detections_emitted += len(out["detections"])
            self.metrics.n_suppressed += len(suppressed)
            self.metrics.absorb(timing)
            self.emitter(out)

            logger.debug(
                "frame={fid} raw={raw} kept={kept} suppressed={sup} total_ms={ms:.1f}",
                fid=pkt.frame_id, raw=len(raw),
                kept=len(out["detections"]), sup=len(suppressed),
                ms=timing.total_ms(),
            )
            if max_frames is not None and self.metrics.n_frames >= max_frames:
                break
        return self.metrics

    # ---- per-layer helpers ----
    def _identify(self, pkt: FramePacket, dets: list[RawDetection]) -> list[IdentifiedDetection]:
        if not dets:
            return []

        out: list[IdentifiedDetection] = []
        if self.classifier is None:
            # detector-only path - no sub-label
            for d in dets:
                out.append(IdentifiedDetection(raw=d))
            self._score(out, pkt)
            return out

        crops = batch_extract(pkt.image, dets, self._classifier_input_size)
        ids = self.classifier(crops)
        for d, (label, conf) in zip(dets, ids, strict=True):
            out.append(IdentifiedDetection(raw=d, id_label=label, id_confidence=conf))
        self._score(out, pkt)
        return out

    def _score(self, items: list[IdentifiedDetection], pkt: FramePacket) -> None:
        if self.threat_scorer is None:
            return
        for it in items:
            inp = ThreatInputs(
                detection_class=it.raw.detection_class,
                detection_conf=it.raw.detection_confidence,
                id_label=it.id_label,
                id_conf=it.id_confidence,
                slant_range_m=float(pkt.telemetry.get("alt_agl_m", 100.0)),
            )
            it.threat_score = self.threat_scorer.score(inp)

    def _geolocate(self, idr: IdentifiedDetection, pkt: FramePacket) -> GeolocatedDetection:
        if self.geolocator is None:
            return GeolocatedDetection(identified=idr)
        return GeolocatedDetection(identified=idr, geolocation=self.geolocator(idr, pkt))

    def _serialise(
        self, pkt: FramePacket, geo: list[GeolocatedDetection],
    ) -> tuple[dict[str, Any], list[tuple[str, str]]]:
        out_dets = [
            OutDetection(
                detection_id=f"d_{pkt.frame_id}_{i:03d}",
                track_id=g.identified.raw.track_id,
                bbox_px=g.identified.raw.bbox_px,
                detection_class=g.identified.raw.detection_class,
                detection_confidence=g.identified.raw.detection_confidence,
                identification=(
                    {"label": g.identified.id_label,
                     "confidence": g.identified.id_confidence}
                    if g.identified.id_label is not None else None
                ),
                geolocation=g.geolocation,
                threat_score=g.identified.threat_score,
            )
            for i, g in enumerate(geo)
        ]
        raw = OutPacket(
            schema_version="1.0",
            mission_id=self._mission_id,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            uas_telemetry=pkt.telemetry,
            detections=out_dets,
            validity_flag=not pkt.telemetry_stale,
        )
        return build_packet(raw, alt_agl_m=pkt.telemetry.get("alt_agl_m"))

    def shutdown(self) -> None:
        logger.info(
            "pipeline shutdown: frames={frames} raw={raw} emitted={emit} "
            "suppressed={sup} mean_stage_ms={mean}",
            frames=self.metrics.n_frames,
            raw=self.metrics.n_detections_raw,
            emit=self.metrics.n_detections_emitted,
            sup=self.metrics.n_suppressed,
            mean={k: round(v, 2) for k, v in self.metrics.mean_stage_ms.items()},
        )
