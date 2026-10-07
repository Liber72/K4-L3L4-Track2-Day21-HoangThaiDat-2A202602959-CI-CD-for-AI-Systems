import io
import json

import boto3
import joblib
import numpy as np
import pandas as pd
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from fastapi.testclient import TestClient
from sklearn.tree import DecisionTreeClassifier

from src import publish_model, serve
from src.data_drift import check_drift
from src.evaluation import detailed_report, sweep_thresholds
from src.model import ThresholdClassifier
from src.train import FEATURE_NAMES
from src import train as training


def test_sweep_finds_threshold_that_recovers_missed_positive():
    best, sweep = sweep_thresholds([0, 0, 1, 1], [0.1, 0.2, 0.4, 0.8])
    assert best == {"threshold": 0.4, "f1_score": 1.0}
    assert [row["threshold"] for row in sweep] == [round(0.1 + i * 0.05, 2) for i in range(17)]
    assert next(row for row in sweep if row["threshold"] == 0.5)["f1_score"] < 1.0


def test_tied_thresholds_prefer_default():
    assert sweep_thresholds([0, 1], [0, 1])[0]["threshold"] == 0.5


@pytest.mark.parametrize("probabilities", [[float("nan")], [-0.1], [1.1]])
def test_invalid_probabilities_are_rejected(probabilities):
    with pytest.raises(ValueError):
        sweep_thresholds([1], probabilities)


def test_detail_report_exposes_false_negatives_and_per_class_metrics():
    matrix, detail = detailed_report([0, 0, 1, 1], [0, 1, 0, 1], 0.4)
    assert matrix == [[1, 1], [1, 1]]
    assert "precision" in detail and "recall" in detail
    assert "thu_nhap_thap (0)" in detail and "thu_nhap_cao (1)" in detail


@pytest.mark.parametrize("positive_count,warning", [(248, False), (298, False), (299, True),
                                                    (198, False), (197, True)])
def test_drift_is_strictly_more_than_five_percentage_points(positive_count, warning, capsys):
    report = check_drift([1] * positive_count + [0] * (1000 - positive_count))
    assert report["drift_warning"] == warning
    assert ("::warning::DATA DRIFT" in capsys.readouterr().out) == warning


@pytest.mark.parametrize("target", [[], [0, 2], [1, float("nan")]])
def test_invalid_drift_input_fails(target):
    with pytest.raises(ValueError):
        check_drift(target)


def test_api_uses_serialized_threshold(tmp_path, monkeypatch):
    frame = pd.DataFrame([[0.0] * 10] * 3 + [[1.0] * 10], columns=FEATURE_NAMES)
    estimator = DecisionTreeClassifier(max_depth=1, random_state=42).fit(frame, [0, 0, 1, 1])
    sample = pd.DataFrame([[0.0] * 10], columns=FEATURE_NAMES)
    assert estimator.predict(sample)[0] == 0
    wrapped = ThresholdClassifier(estimator, threshold=0.3)
    path = tmp_path / "model.joblib"
    joblib.dump(wrapped, path)
    monkeypatch.setenv("MODEL_SOURCE", "local")
    monkeypatch.setenv("MODEL_PATH", str(path))
    with TestClient(serve.app) as client:
        assert client.post("/score", json={"features": [0] * 10}).json()["prediction"] == 1


@pytest.fixture
def s3_client():
    return boto3.client("s3", region_name="us-east-1", aws_access_key_id="test",
                        aws_secret_access_key="test")


@pytest.mark.parametrize("current,candidate,allowed", [(0.8, 0.7, False), (0.7, 0.7, True),
                                                       (0.7, 0.8, True)])
def test_regression_guard_reads_current_report_and_compares(s3_client, current, candidate, allowed):
    with Stubber(s3_client) as stub:
        body = io.BytesIO(json.dumps({"f1_score": current}).encode())
        stub.add_response("get_object", {"Body": body},
                          {"Bucket": "test-bucket", "Key": "artifacts/current/report.json"})
        decision = publish_model.release_decision(s3_client, "test-bucket", {"f1_score": candidate})
        assert decision["deploy"] == allowed
        assert body.closed


def test_missing_current_report_allows_first_deployment(s3_client):
    with Stubber(s3_client) as stub:
        stub.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
        assert publish_model.release_decision(s3_client, "test-bucket", {"f1_score": 0.7})["deploy"]


def test_access_denied_does_not_bypass_regression_guard(s3_client):
    with Stubber(s3_client) as stub:
        stub.add_client_error("get_object", service_error_code="AccessDenied", http_status_code=403)
        with pytest.raises(ClientError):
            publish_model.release_decision(s3_client, "test-bucket", {"f1_score": 0.8})


def test_regressed_candidate_never_uploads(tmp_path, monkeypatch):
    model, report = tmp_path / "model.joblib", tmp_path / "report.json"
    model.write_bytes(b"candidate")
    report.write_text('{"f1_score": 0.7}', encoding="utf-8")

    class FakeS3:
        def get_object(self, **kwargs):
            return {"Body": io.BytesIO(b'{"f1_score": 0.8}')}

        def upload_file(self, *args):
            pytest.fail("A regressed candidate must not replace the deployed model")

    monkeypatch.setattr(publish_model.boto3, "client", lambda service: FakeS3())
    assert publish_model.publish_model("test-bucket", model, report) is False


def test_changed_holdout_blocks_comparison(s3_client):
    with Stubber(s3_client) as stub:
        stub.add_response("get_object", {"Body": io.BytesIO(
            b'{"f1_score": 0.7, "eval_data_sha256": "previous"}')})
        with pytest.raises(ValueError, match="Holdout changed"):
            publish_model.release_decision(s3_client, "test-bucket",
                                          {"f1_score": 0.8, "eval_data_sha256": "new"})


def test_remote_tracking_does_not_use_runner_artifact_directory(monkeypatch):
    uri = "https://dagshub.com/example/lab.mlflow"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.setenv("MLFLOW_TRACKING_USERNAME", "example")
    monkeypatch.setenv("MLFLOW_TRACKING_PASSWORD", "test-token")
    monkeypatch.setattr(training.mlflow, "set_tracking_uri", lambda value: None)
    monkeypatch.setattr(training.mlflow, "get_tracking_uri", lambda: uri)
    monkeypatch.setattr(training.mlflow, "get_experiment_by_name", lambda name: None)
    calls = []

    def create_experiment(name, **kwargs):
        calls.append(kwargs)
        return "remote-experiment"

    monkeypatch.setattr(training.mlflow, "create_experiment", create_experiment)
    assert training.configure_tracking() == "remote-experiment"
    assert calls == [{}]


def test_dagshub_missing_auth_fails_before_network(monkeypatch):
    monkeypatch.setattr(training.mlflow, "set_tracking_uri", lambda value: None)
    monkeypatch.setattr(training.mlflow, "get_tracking_uri",
                        lambda: "https://dagshub.com/example/lab.mlflow")
    monkeypatch.delenv("MLFLOW_TRACKING_USERNAME", raising=False)
    monkeypatch.delenv("MLFLOW_TRACKING_PASSWORD", raising=False)
    monkeypatch.setattr(training.mlflow, "get_experiment_by_name",
                        lambda name: pytest.fail("No HTTP request without configured auth"))
    with pytest.raises(ValueError, match="DagsHub requires"):
        training.configure_tracking()
