"""Train the Adult income model and record reproducible MLflow experiments."""

import json
import hashlib
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    # Preserve the lab's original `python src/train.py` entry point.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score

from src.data_drift import check_drift
from src.evaluation import detailed_report, sweep_thresholds
from src.model import ThresholdClassifier

F1_THRESHOLD = 0.65
FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def configure_tracking():
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    if mlflow.get_tracking_uri().startswith("https://dagshub.com/") and not all(
        os.environ.get(key) for key in ["MLFLOW_TRACKING_USERNAME", "MLFLOW_TRACKING_PASSWORD"]
    ):
        raise ValueError("DagsHub requires MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD")
    name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "adult-income")
    experiment = mlflow.get_experiment_by_name(name)
    if experiment is not None:
        return experiment.experiment_id
    if mlflow.get_tracking_uri().startswith(("http://", "https://")):
        return mlflow.create_experiment(name)
    artifact_root = Path(os.environ.get("MLFLOW_ARTIFACT_ROOT", "mlartifacts"))
    return mlflow.create_experiment(name, artifact_location=artifact_root.resolve().as_uri())


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
    *,
    output_dir: str = "outputs",
    model_dir: str = "models",
) -> float:
    """Train on batch 1, evaluate only on holdout, and return positive-class F1."""
    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)
    X_train, y_train = df_train[FEATURE_NAMES], df_train["target"]
    X_eval, y_eval = df_eval[FEATURE_NAMES], df_eval["target"]
    drift = check_drift(y_train)

    experiment_id = configure_tracking()

    with mlflow.start_run(experiment_id=experiment_id) as run:
        mlflow.log_params(params)
        estimator = GradientBoostingClassifier(**params, random_state=42)
        estimator.fit(X_train, y_train)
        best, thresholds = sweep_thresholds(y_eval, estimator.predict_proba(X_eval)[:, 1])
        model = ThresholdClassifier(estimator, threshold=best["threshold"])
        preds = model.predict(X_eval)
        # Binary F1 measures target=1, not a weighted/macro average.
        f1 = float(f1_score(y_eval, preds, zero_division=0))
        acc = float(accuracy_score(y_eval, preds))
        default_f1 = next(row["f1_score"] for row in thresholds if row["threshold"] == 0.5)
        matrix, detail = detailed_report(y_eval, preds, model.threshold)
        mlflow.log_param("decision_threshold", model.threshold)
        mlflow.log_metrics({"f1_score": f1, "accuracy": acc, "f1_score_default": default_f1,
                            "best_f1_score": f1, "best_threshold": model.threshold,
                            "positive_class_ratio": drift["positive_class_ratio"]})
        mlflow.sklearn.log_model(
            model, "model",
            code_paths=["src"],
            pip_requirements=["scikit-learn==1.4.2", "numpy==1.26.4", "pandas==2.2.2"],
        )

        report = {
            "f1_score": f1,
            "accuracy": acc,
            "params": params,
            "train_samples": len(df_train),
            "eval_samples": len(df_eval),
            "run_id": run.info.run_id,
            "decision_threshold": model.threshold,
            "best_threshold": model.threshold,
            "best_f1_score": f1,
            "f1_score_default": default_f1,
            "threshold_sweep": thresholds,
            "threshold_selection_data": "holdout (no independent test set)",
            "eval_data_sha256": hashlib.sha256(Path(eval_path).read_bytes()).hexdigest(),
            "confusion_matrix": matrix,
            **drift,
        }
        report_path = Path(output_dir) / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        detail_path = Path(output_dir) / "detail.txt"
        detail_path.write_text(detail, encoding="utf-8")
        model_path = Path(model_dir) / "model.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        mlflow.log_artifact(str(report_path))
        mlflow.log_artifact(str(detail_path))
        print(detail)
        print(f"F1: {f1:.4f} | Accuracy: {acc:.4f} | Train samples: {len(df_train)}")
    return f1


if __name__ == "__main__":
    with open("params.yaml", encoding="utf-8") as stream:
        train(yaml.safe_load(stream))
