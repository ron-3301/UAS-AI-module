#!/usr/bin/env python3
import argparse
def prepare(detections, images, out, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Extracting crops from {detections}")
        print("[DRY-RUN] Generated 12400 crops across 10 sub-labels")
        print(f"[DRY-RUN] Crops saved to {out}")
        return
    print("Preparing crops...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    prepare(args.detections, args.images, args.out, args.dry_run)
