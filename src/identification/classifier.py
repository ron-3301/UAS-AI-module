# identification classifier. same dual pattern as the detector:
#   OnnxClassifier  - real EfficientNet-B3 ONNX engine
#   MockClassifier  - scripted; tests + replay path
# both expose __call__(crops) -> [(label, conf), ...]
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

# stable sub-label index. tests + DEC-003 rely on the "Civilian" prefix match.
DEFAULT_LABELS: list[str] = [
    "Unknown",
    "Civilian", "Civilian-Sedan", "Civilian-Truck",
    "Combatant-Unarmed", "Combatant-Armed",
    "Humvee", "Toyota-Hilux", "Ural-4320", "BTR-wheeled",
    "T-72", "T-90", "BMP-2", "M1-Abrams", "Bulldozer",
]


class OnnxClassifier:
    def __init__(
        self,
        weights: str | Path,
        *,
        input_size: int = 224,
        labels: list[str] | None = None,
        device: str = "cpu",
    ) -> None:
        self.weights = str(weights)
        self.input_size = input_size
        self.labels = labels or DEFAULT_LABELS
        self.device = device
        self._session: Any | None = None

    def _load(self) -> Any:  # pragma: no cover - real weights only
        if self._session is None:
            import onnxruntime as ort
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] \
                if self.device != "cpu" else ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(self.weights, providers=providers)
        return self._session

    def __call__(self, crops: list[Any]) -> list[tuple[str, float]]:  # pragma: no cover
        import numpy as np
        if not crops:
            return []
        sess = self._load()
        # ImageNet-style normalisation, CHW float32 batch
        batch = np.stack([_to_chw_norm(c) for c in crops]).astype("float32")
        in_name = sess.get_inputs()[0].name
        logits = sess.run(None, {in_name: batch})[0]
        probs = _softmax(logits)
        idxs = probs.argmax(axis=1)
        return [(self.labels[i], float(probs[k, i])) for k, i in enumerate(idxs)]


def _softmax(x: Any) -> Any:
    import numpy as np
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def _to_chw_norm(img: Any) -> Any:
    import numpy as np
    mean = np.array([0.485, 0.456, 0.406], dtype="float32") * 255.0
    std  = np.array([0.229, 0.224, 0.225], dtype="float32") * 255.0
    a = img.astype("float32")
    a = (a - mean) / std
    return a.transpose(2, 0, 1)


class MockClassifier:
    # deterministic. for tests + integration replay.
    def __init__(self, fn: Callable[[Any], tuple[str, float]]) -> None:
        self.fn = fn

    def __call__(self, crops: list[Any]) -> list[tuple[str, float]]:
        return [self.fn(c) for c in crops]
