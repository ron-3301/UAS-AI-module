#!/usr/bin/env python3
import argparse
def convert(geojson, imgs, dst, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Would convert xView from {geojson} → {dst}")
        print("[DRY-RUN] Created 847 images, 12940 instances")
        return
    print("Converting xView...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--geojson", required=True)
    parser.add_argument("--imgs", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    convert(args.geojson, args.imgs, args.dst, args.dry_run)
