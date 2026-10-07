"""Fail deployment unless the positive-class F1 meets the lab threshold."""

import argparse
import json
import math
from pathlib import Path

F1_THRESHOLD = 0.65


def check_quality(f1: float) -> None:
    if not math.isfinite(f1) or not 0.0 <= f1 <= 1.0:
        raise ValueError(f"Invalid f1_score: {f1}")
    if f1 < F1_THRESHOLD:
        raise ValueError(f"FAILED: f1_score {f1:.4f} < {F1_THRESHOLD}. Release blocked.")
    print(f"PASSED: f1_score {f1:.4f} >= {F1_THRESHOLD}.")


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--f1", type=float)
    source.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        f1 = args.f1
        if args.report is not None:
            f1 = float(json.loads(args.report.read_text(encoding="utf-8"))["f1_score"])
        check_quality(f1)
    except (ValueError, KeyError, OSError, TypeError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
