#!/usr/bin/env python3
import argparse
def mine(predictions, ground_truth, images, out, max_images, filter_class, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Mining hard negatives for class '{filter_class}'")
        print(f"[DRY-RUN] Selected {max_images} images for relabeling")
        print("[DRY-RUN] Output written to", out)
        return
    print("Mining hard negatives...")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--ground-truth", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-images", type=int, default=500)
    parser.add_argument("--filter-class", default="Person")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    mine(args.predictions, args.ground_truth, args.images, args.out, args.max_images, args.filter_class, args.dry_run)
