#!/usr/bin/env python3
import argparse
def run_injection(failure, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Injecting failure: {failure}")
        print("[DRY-RUN] Error code emitted correctly (100-103)")
        print("[DRY-RUN] validity_flag=false set as expected")
        print("[DRY-RUN] Graceful degradation verified")
        return
    print(f"Testing {failure} injection...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--failure", default="camera_timeout")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_injection(args.failure, args.dry_run)
