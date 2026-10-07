"""Run three local trials, keep their artifacts, and select the highest F1."""

import json
from pathlib import Path
import shutil

import yaml

from src.train import F1_THRESHOLD, train

TRIALS = [
    {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 3},
    {"n_estimators": 50, "learning_rate": 0.05, "max_depth": 2},
    {"n_estimators": 200, "learning_rate": 0.1, "max_depth": 5},
]


def main():
    reports = []
    for index, params in enumerate(TRIALS, start=1):
        print(f"Trial {index}: {params}")
        output_dir = Path("outputs/experiments") / f"run-{index}"
        model_dir = Path("models/experiments") / f"run-{index}"
        train(params, output_dir=str(output_dir), model_dir=str(model_dir))
        report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
        reports.append({"trial": index, **report})

    best = max(reports, key=lambda report: report["f1_score"])
    summary = {"trials": reports, "best_trial": best["trial"]}
    Path("outputs/experiments.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    Path("params.yaml").write_text(yaml.safe_dump(best["params"], sort_keys=False), encoding="utf-8")
    shutil.copyfile(
        Path("models/experiments") / f"run-{best['trial']}" / "model.joblib",
        "models/model.joblib",
    )
    shutil.copyfile(
        Path("outputs/experiments") / f"run-{best['trial']}" / "report.json",
        "outputs/report.json",
    )
    print(f"Selected trial {best['trial']}: F1={best['f1_score']:.4f}, {best['params']}")
    if best["f1_score"] < F1_THRESHOLD:
        print("The best trial is still below the quality gate. Try stronger parameters before CI.")


if __name__ == "__main__":
    main()
