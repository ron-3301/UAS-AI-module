from __future__ import annotations

# layer 5 stub. draw boxes/labels/coords, push via RTSP (GStreamer).
# real impl lands Phase 3 W9.



class VideoAnnotator:
    def __init__(self, rtsp_port: int = 8554) -> None:
        self.rtsp_port = rtsp_port

    def push(self, frame, detections):  # pragma: no cover - stub
        raise NotImplementedError("video annotator lands Phase 3 W9")
