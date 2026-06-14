#!/usr/bin/env python3
# Measure end-to-end latency on host or Jetson -> CSV + HTML report.
# stub. real impl in Phase 5 W13-W14.
from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=10000)
    ap.add_argument("--out",    default="artefacts/latency.csv")
    args = ap.parse_args()
    print(f"[stub] would benchmark {args.frames} frames -> {args.out}")


if __name__ == "__main__":
    main()
