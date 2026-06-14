import sys
sys.path.insert(0, "src")
from src.pipeline import Pipeline
from src.config import load_config

def test_end_to_end_runs():
    cfg = load_config("configs/inference.yaml")
    p = Pipeline(cfg)
    packet = p.process_frame()
    assert "detections" in packet and "schema_version" in packet