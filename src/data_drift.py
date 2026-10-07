"""Warn when the positive-class proportion shifts by more than five points."""

import argparse
import json
import math
from pathlib import Path

import pandas as pd

REFERENCE_RATIO = 0.248
MAX_SHIFT = 0.05


def check_drift(target) -> dict:
    values = pd.Series(target)
    if values.empty or not values.isin([0, 1]).all():
        raise ValueError("Training target must contain nonempty binary labels 0/1")
    ratio = float(values.mean())
    shift = abs(ratio - REFERENCE_RATIO)
    warning = shift > MAX_SHIFT and not math.isclose(shift, MAX_SHIFT, abs_tol=1e-12)
    print(f"Positive-class ratio: {ratio:.2%}; reference: {REFERENCE_RATIO:.2%}; "
          f"shift: {shift * 100:.2f} percentage points")
    if warning:
        print("::warning::DATA DRIFT: positive-class ratio differs by more than 5 percentage points")
    return {"positive_class_ratio": ratio, "reference_ratio": REFERENCE_RATIO,
            "shift_percentage_points": shift * 100, "drift_warning": warning}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/train_batch1.csv"))
    args = parser.parse_args()
    report = check_drift(pd.read_csv(args.data)["target"])
    path = Path("outputs/drift.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
