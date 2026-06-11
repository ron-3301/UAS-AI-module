import argparse
from src.config import load_config
from src.pipeline import Pipeline

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    pipeline = Pipeline(cfg)

    if args.dry_run:
        print("DRY-RUN: Pipeline initialized successfully.")
        print("Mission:", cfg["mission_id"])
        return

    packet = pipeline.process_frame()
    print("Emitted packet:", packet)

if __name__ == "__main__":
    main()
