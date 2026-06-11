import yaml
from typing import Dict, Any

def load_config(path: str) -> Dict[str, Any]:
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if not str(cfg.get("version", "")).startswith("1."):
        raise ValueError("Unsupported config version")
    return cfg
