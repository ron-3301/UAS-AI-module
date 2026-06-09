#!/usr/bin/env python3
# W6 model benchmark - compare detector archs on the same dataset.
#
# trains (or fine-tunes) each candidate for --epochs, evaluates mAP@50,
# mAP@50-95, and wall-clock per-image latency. emits CSV + markdown so the
# W6 DEC entry is data-driven.
#
# candidates (default): yolov8s, yolov8m, yolov10m, rt-detr-l.
#
# --dry-run short-circuits ultralytics with deterministic synthetic numbers
# so the CSV/markdown emission can be tested in CI w/o a GPU.
#
# real run:
#   python scripts/benchmark_models.py --data data/processed/current/data.yaml \
#       --epochs 30 --device 0 --out-dir runs/w6_benchmark
#
# sandbox dry-run:
#   python scripts/benchmark_models.py --data /dev/null --dry-run --out-dir /tmp/w6
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_CANDIDATES = ["yolov8s", "yolov8m", "yolov10m", "rt-detr-l"]


@dataclass
class BenchmarkRow:
    arch: str
    epochs: int
    map50: float
    map50_95: float
    latency_ms_p50: float
    latency_ms_p95: float
    params_m: float
    notes: str = ""


def _train_and_eval_real(arch: str, data_yaml: Path, epochs: int, device: str) -> BenchmarkRow:  # pragma: no cover - GPU
    from ultralytics import YOLO  # type: ignore
    # rt-detr also uses .pt files. keeping the ternary in case naming diverges.
    pretrained = f"{arch}.pt"
    model = YOLO(pretrained)
    kw: dict[str, Any] = dict(
        data=str(data_yaml), epochs=epochs, imgsz=640,
        device=device, verbose=False, name=f"w6_{arch}", exist_ok=True,
    )
    res = model.train(**kw)
    m = getattr(res, "results_dict", {}) or {}
    map50    = float(m.get("metrics/mAP50(B)", 0.0))
    map50_95 = float(m.get("metrics/mAP50-95(B)", 0.0))

    # latency: predict on the val set, measure per-image
    val_imgs = data_yaml.parent / "images" / "val"
    samples = sorted(val_imgs.glob("*.png"))[:200] if val_imgs.exists() else []
    lats: list[float] = []
    for img in samples:
        t0 = time.perf_counter()
        model.predict(source=str(img), imgsz=640, device=device, verbose=False)
        lats.append((time.perf_counter() - t0) * 1000.0)
    p50 = _pct(lats, 50) if lats else 0.0
    p95 = _pct(lats, 95) if lats else 0.0

    params_m = float(sum(p.numel() for p in model.model.parameters())) / 1e6
    return BenchmarkRow(arch=arch, epochs=epochs,
                        map50=map50, map50_95=map50_95,
                        latency_ms_p50=p50, latency_ms_p95=p95,
                        params_m=params_m)


def _train_and_eval_dry(arch: str, epochs: int) -> BenchmarkRow:
    # deterministic fake numbers so the CSV/markdown writer is exercised in CI.
    # rt-detr-l is deliberately over the 110ms budget to verify the
    # recommendation filter actually filters.
    table = {
        "yolov8s":   (0.74, 0.51,  65,  85, 11.2),
        "yolov8m":   (0.83, 0.62,  92, 108, 25.9),
        "yolov10m":  (0.84, 0.63,  95, 112, 26.4),
        "rt-detr-l": (0.85, 0.64, 134, 158, 31.0),
    }
    map50, map50_95, p50, p95, params = table.get(arch, (0.5, 0.3, 100, 130, 20.0))
    return BenchmarkRow(arch=arch, epochs=epochs,
                        map50=map50, map50_95=map50_95,
                        latency_ms_p50=p50, latency_ms_p95=p95,
                        params_m=params, notes="dry-run synthetic numbers")


def _pct(xs: list[float], pct: int) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = int(round((pct / 100.0) * (len(s) - 1)))
    return s[max(0, min(len(s) - 1, k))]


def write_report(rows: list[BenchmarkRow], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "benchmark.csv"
    md_path  = out_dir / "benchmark.md"

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        fields = list(asdict(rows[0]).keys()) if rows else []
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

    # latency budget per docs/14 §1
    budget_ms = 110
    lines = [
        "# W6 Model Benchmark", "",
        f"Budget (p95 detector latency): **{budget_ms} ms** "
        "(see `docs/14_latency_power_budget.md`).", "",
        "| arch | mAP@50 | mAP@50-95 | p50 ms | p95 ms | params (M) | within budget |",
        "|------|------:|---------:|-------:|-------:|-----------:|:-------------:|",
    ]
    for r in rows:
        ok = "✅" if r.latency_ms_p95 <= budget_ms else "❌"
        lines.append(
            f"| {r.arch} | {r.map50:.3f} | {r.map50_95:.3f} | {r.latency_ms_p50:.1f} | "
            f"{r.latency_ms_p95:.1f} | {r.params_m:.1f} | {ok} |"
        )
    lines.append("")

    # pick the winner - highest mAP among archs within budget
    in_budget = [r for r in rows if r.latency_ms_p95 <= budget_ms]
    if in_budget:
        winner = max(in_budget, key=lambda r: r.map50)
        lines.append(f"**Recommended:** `{winner.arch}` — mAP@50 = {winner.map50:.3f}, "
                     f"p95 latency = {winner.latency_ms_p95:.1f} ms.")
    else:
        lines.append("**Recommended:** *none* — every candidate exceeds the latency budget. "
                     "Re-run with a smaller image size or weaker backbone.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def run(*, data_yaml: Path, epochs: int, device: str, candidates: list[str],
        out_dir: Path, dry_run: bool) -> tuple[list[BenchmarkRow], Path, Path]:
    rows: list[BenchmarkRow] = []
    for arch in candidates:
        if dry_run:
            row = _train_and_eval_dry(arch, epochs)
        else:                                                # pragma: no cover - GPU
            row = _train_and_eval_real(arch, data_yaml, epochs, device)
        rows.append(row)
    csv_path, md_path = write_report(rows, out_dir)
    return rows, csv_path, md_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data",       type=Path, required=True)
    ap.add_argument("--epochs",     type=int, default=30)
    ap.add_argument("--device",     default="0")
    ap.add_argument("--candidates", nargs="+", default=DEFAULT_CANDIDATES)
    ap.add_argument("--out-dir",    type=Path, default=Path("runs/w6_benchmark"))
    ap.add_argument("--dry-run",    action="store_true",
                    help="use synthetic numbers (CI / sandbox).")
    args = ap.parse_args()

    rows, csv_path, md_path = run(
        data_yaml=args.data, epochs=args.epochs, device=args.device,
        candidates=args.candidates, out_dir=args.out_dir, dry_run=args.dry_run,
    )
    print(json.dumps({
        "csv": str(csv_path),
        "md":  str(md_path),
        "rows": [asdict(r) for r in rows],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
