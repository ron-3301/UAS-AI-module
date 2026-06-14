# --- OLD CODE FROM SRC ---
# UAS AI Module — onboard recognition + identification + targeting.
# 5 layers wired together by src/pipeline.py:
#   ingestion -> detection -> identification -> geolocation -> output
# see docs/ for the design.

__version__ = "0.1.0"

# --- END OLD CODE ---

"""Safety-first advisory UAS AI module rebuild."""

from .pipeline import Pipeline

__all__ = ["Pipeline"]
__version__ = "0.1.0"
