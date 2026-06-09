#!/usr/bin/env python3
# Camera calibration via checkerboard -> cam_intrinsics.yaml.
# stub. real impl in Phase 1 W1 (on the bench rig).
from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkerboard", default="9x6")
    ap.add_argument("--output", default="configs/cam_intrinsics.yaml")
    args = ap.parse_args()
    print(f"[stub] calibrate with {args.checkerboard} -> {args.output}")


if __name__ == "__main__":
    main()
