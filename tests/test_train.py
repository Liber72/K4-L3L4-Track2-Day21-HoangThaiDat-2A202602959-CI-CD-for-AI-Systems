import json

import joblib
import mlflow
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import accuracy_score, f1_score

from src.train import FEATURE_NAMES, train


def _make_temp_data(tmp_path):
    rng = np.random.default_rng(0)
    X = rng.random((200, len(FEATURE_NAMES)))
    y = rng.integers(0, 2, size=200)
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["target"] = y
    train_path, eval_path = tmp_path / "train.csv", tmp_path / "holdout.csv"
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)
    return str(train_path), str(eval_path)


@pytest.fixture(scope="module")
def trained_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("training")
    train_path, eval_path = _make_temp_data(root)
    # Keep test runs and artifacts separate from the lab's real experiments.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{(root / 'mlflow.db').as_posix()}")
        patch.setenv("MLFLOW_ARTIFACT_ROOT", str(root / "mlartifacts"))
        patch.setenv("MLFLOW_EXPERIMENT_NAME", "test-income")
        f1 = train(
            {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
            data_path=train_path, eval_path=eval_path,
            output_dir=str(root / "outputs"), model_dir=str(root / "models"),
        )
        yield root, f1, eval_path


def test_train_returns_float(trained_run):
    _, f1, _ = trained_run
    assert isinstance(f1, float)
    assert 0.0 <= f1 <= 1.0


def test_report_file_created(trained_run):
    root, f1, eval_path = trained_run
    report = json.loads((root / "outputs/report.json").read_text(encoding="utf-8"))
    holdout = pd.read_csv(eval_path)
    model = joblib.load(root / "models/model.joblib")
    predictions = model.predict(holdout[FEATURE_NAMES])
    assert report["f1_score"] == pytest.approx(f1)
    assert f1 == pytest.approx(f1_score(holdout["target"], predictions))
    assert report["accuracy"] == pytest.approx(accuracy_score(holdout["target"], predictions))
    assert report["train_samples"] == 160
    assert report["eval_samples"] == 40
    run = mlflow.get_run(report["run_id"])
    assert run.data.metrics["f1_score"] == pytest.approx(f1)
    assert run.data.metrics["accuracy"] == pytest.approx(report["accuracy"])


def test_model_file_created(trained_run):
    root, _, eval_path = trained_run
    model = joblib.load(root / "models/model.joblib")
    holdout = pd.read_csv(eval_path)
    assert list(model.feature_names_in_) == FEATURE_NAMES
    assert len(model.predict(holdout[FEATURE_NAMES])) == 40
