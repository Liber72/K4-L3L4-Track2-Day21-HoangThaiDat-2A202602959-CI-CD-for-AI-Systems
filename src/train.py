"""Train the Adult income model and record reproducible MLflow experiments."""

import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score

F1_THRESHOLD = 0.65
FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


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

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "adult-income")
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        artifact_root = Path(os.environ.get("MLFLOW_ARTIFACT_ROOT", "mlartifacts"))
        experiment_id = mlflow.create_experiment(
            experiment_name, artifact_location=artifact_root.resolve().as_uri()
        )
    else:
        experiment_id = experiment.experiment_id

    with mlflow.start_run(experiment_id=experiment_id) as run:
        mlflow.log_params(params)
        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_eval)
        # Binary F1 measures target=1, not a weighted/macro average.
        f1 = float(f1_score(y_eval, preds, zero_division=0))
        acc = float(accuracy_score(y_eval, preds))
        mlflow.log_metrics({"f1_score": f1, "accuracy": acc})
        mlflow.sklearn.log_model(
            model, "model",
            pip_requirements=["scikit-learn==1.4.2", "numpy==1.26.4", "pandas==2.2.2"],
        )

        report = {
            "f1_score": f1,
            "accuracy": acc,
            "params": params,
            "train_samples": len(df_train),
            "eval_samples": len(df_eval),
            "run_id": run.info.run_id,
        }
        report_path = Path(output_dir) / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        model_path = Path(model_dir) / "model.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        mlflow.log_artifact(str(report_path))
        print(f"F1: {f1:.4f} | Accuracy: {acc:.4f} | Train samples: {len(df_train)}")
    return f1


if __name__ == "__main__":
    with open("params.yaml", encoding="utf-8") as stream:
        train(yaml.safe_load(stream))
