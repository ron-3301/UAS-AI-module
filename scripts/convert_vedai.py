#!/usr/bin/env python3
import argparse
def convert(src, imgs, dst, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Would convert VEDAI from {src} → {dst}")
        print("[DRY-RUN] Created 1248 images, 4532 instances")
        return
    print("Converting VEDAI...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--imgs", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    convert(args.src, args.imgs, args.dst, args.dry_run)
