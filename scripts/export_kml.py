#!/usr/bin/env python3
# Mission SQLite -> Google Earth KML, coloured by threat_score.
from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db",  required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    print(f"[stub] would export {args.db} -> {args.out}")


if __name__ == "__main__":
    main()
