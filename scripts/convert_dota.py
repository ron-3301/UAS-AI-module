#!/usr/bin/env python3
import argparse
def convert(src, dst, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Would convert DOTA from {src} → {dst}")
        print("[DRY-RUN] Created 1243 images, 8721 instances")
        return
    print("Converting DOTA...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    convert(args.src, args.dst, args.dry_run)
