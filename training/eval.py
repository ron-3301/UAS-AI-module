# W8 - detector eval.
#
# computes mAP@50, mAP@50-95, per-class AP, and a confusion matrix via
# the ultralytics model.val() path. emits:
#   results.json          - flat summary metrics
#   confusion_matrix.csv  - NxN matrix
#   per_class_ap.csv      - sorted per-class AP
#   error_report.md       - lowest-AP classes + top off-diagonal confusions
#
# --dry-run short-circuits the inner ultralytics call so the report writers
# can be exercised in CI without weights.
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

CLASS_NAMES: list[str] = [
    "Person", "Vehicle-Wheeled", "Vehicle-Tracked",
    "Aircraft-Rotary", "Aircraft-Fixed", "Watercraft", "Structure-Temp",
]


@dataclass
class EvalResult:
    map50: float
    map50_95: float
    per_class_ap: dict[str, float]
    confusion: list[list[int]]      # row=true, col=pred, last row/col = background
    notes: str = ""


def _eval_real(weights: Path, data_yaml: Path, device: str) -> EvalResult:  # pragma: no cover - GPU
    from ultralytics import YOLO  # type: ignore
    model = YOLO(str(weights))
    m = model.val(data=str(data_yaml), device=device, verbose=False)
    rd = m.results_dict

    # per-class AP
    pc: dict[str, float] = {}
    if hasattr(m.box, "ap50") and m.box.ap50 is not None:
        for i, ap in enumerate(m.box.ap50):
            if i < len(CLASS_NAMES):
                pc[CLASS_NAMES[i]] = float(ap)

    # confusion matrix
    conf: list[list[int]] = []
    cm = getattr(m, "confusion_matrix", None)
    if cm is not None and hasattr(cm, "matrix"):
        conf = [[int(v) for v in row] for row in cm.matrix.tolist()]

    return EvalResult(
        map50=float(rd.get("metrics/mAP50(B)", 0.0)),
        map50_95=float(rd.get("metrics/mAP50-95(B)", 0.0)),
        per_class_ap=pc,
        confusion=conf,
    )


def _eval_dry() -> EvalResult:
    # synthetic numbers so the report writers get exercised in CI
    pc = {
        "Person":          0.62,
        "Vehicle-Wheeled": 0.88,
        "Vehicle-Tracked": 0.74,
        "Aircraft-Rotary": 0.80,
        "Aircraft-Fixed":  0.91,
        "Watercraft":      0.83,
        "Structure-Temp":  0.55,
    }
    cm = [
        [80,   1,  0,  0,  0,  0,  0,  9],
        [ 0, 220,  4,  0,  0,  0,  1,  5],
        [ 0,   6, 60,  0,  0,  0,  0,  4],
        [ 0,   0,  0, 40,  1,  0,  0,  2],
        [ 0,   0,  0,  1, 90,  0,  0,  1],
        [ 0,   1,  0,  0,  0, 70,  0,  3],
        [ 0,   2,  0,  0,  0,  0, 30,  7],
        [10,  14,  5,  3,  4,  4,  6,  0],   # background row
    ]
    return EvalResult(
        map50=0.79, map50_95=0.58,
        per_class_ap=pc, confusion=cm,
        notes="dry-run synthetic numbers",
    )


def write_reports(result: EvalResult, out_dir: Path, *, target_map50: float = 0.80) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json":      out_dir / "results.json",
        "per_class": out_dir / "per_class_ap.csv",
        "confusion": out_dir / "confusion_matrix.csv",
        "report":    out_dir / "error_report.md",
    }

    paths["json"].write_text(
        json.dumps({
            "map50": result.map50, "map50_95": result.map50_95,
            "per_class_ap": result.per_class_ap, "notes": result.notes,
        }, indent=2),
        encoding="utf-8",
    )

    # per_class CSV sorted worst-first
    with open(paths["per_class"], "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "ap50"])
        for cls, ap in sorted(result.per_class_ap.items(), key=lambda kv: kv[1]):
            w.writerow([cls, f"{ap:.4f}"])

    # confusion matrix CSV
    with open(paths["confusion"], "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([""] + list(CLASS_NAMES) + ["background"])
        row_labels = list(CLASS_NAMES) + ["background"]
        for i, row in enumerate(result.confusion):
            lbl = row_labels[i] if i < len(row_labels) else f"row_{i}"
            w.writerow([lbl] + [str(v) for v in row])

    # markdown report
    lines = [
        "# Evaluation Report", "",
        f"- **mAP@50:** {result.map50:.3f}  (target: {target_map50:.2f}, "
        f"{'✅ PASS' if result.map50 >= target_map50 else '❌ FAIL'})",
        f"- **mAP@50-95:** {result.map50_95:.3f}",
        "",
        "## Per-class AP (ascending — worst first)", "",
        "| class | AP@50 |", "|------|------:|",
    ]
    for cls, ap in sorted(result.per_class_ap.items(), key=lambda kv: kv[1]):
        lines.append(f"| {cls} | {ap:.3f} |")

    # top off-diagonal confusions
    if result.confusion:
        nn = len(CLASS_NAMES)
        offdiag: list[tuple[str, str, int]] = []
        for i in range(min(nn, len(result.confusion))):
            for j in range(min(nn, len(result.confusion[i]))):
                if i == j:
                    continue
                offdiag.append((CLASS_NAMES[i], CLASS_NAMES[j], int(result.confusion[i][j])))
        offdiag.sort(key=lambda t: t[2], reverse=True)
        lines += ["", "## Top class confusions (true → predicted)", "",
                  "| true | predicted | count |", "|------|-----------|------:|"]
        for true, pred, n in offdiag[:10]:
            if n == 0:
                break
            lines.append(f"| {true} | {pred} | {n} |")

    # W9 follow-up: name the worst class for the hard-neg mining step
    if result.per_class_ap:
        worst = min(result.per_class_ap.items(), key=lambda kv: kv[1])
        lines += [
            "", "## Recommended next step (W9)",
            f"Worst-performing class is **{worst[0]}** at AP@50 = {worst[1]:.3f}. "
            f"Mine 500 hard negatives for that class via "
            f"`scripts/mine_hard_negatives.py --class {worst[0]}` and retrain.",
        ]

    paths["report"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return paths


def run(*, weights: Path, data_yaml: Path, device: str, out_dir: Path,
        target_map50: float, dry_run: bool) -> EvalResult:
    result = _eval_dry() if dry_run else _eval_real(weights, data_yaml, device)
    paths = write_reports(result, out_dir, target_map50=target_map50)
    logger.info("eval reports written: {}", {k: str(p) for k, p in paths.items()})
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", type=Path, default=Path("runs/detector/best.pt"))
    ap.add_argument("--data",    type=Path, required=True)
    ap.add_argument("--device",  default="0")
    ap.add_argument("--out-dir", type=Path, default=Path("runs/eval"))
    ap.add_argument("--target-map50", type=float, default=0.80)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    res = run(weights=args.weights, data_yaml=args.data, device=args.device,
              out_dir=args.out_dir, target_map50=args.target_map50,
              dry_run=args.dry_run)
    print(f"mAP@50={res.map50:.3f}  mAP@50-95={res.map50_95:.3f}")
    return 0 if res.map50 >= args.target_map50 else 1


if __name__ == "__main__":
    sys.exit(main())
