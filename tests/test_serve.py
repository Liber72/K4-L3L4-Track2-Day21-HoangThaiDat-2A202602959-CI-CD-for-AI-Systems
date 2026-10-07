import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError

from sklearn.tree import DecisionTreeClassifier
from src import serve
from src.train import FEATURE_NAMES


@pytest.fixture
def client(tmp_path, monkeypatch):
    X = pd.DataFrame([[0.0] * 10, [1.0] * 10], columns=FEATURE_NAMES)
    model = DecisionTreeClassifier(random_state=42).fit(X, [0, 1])
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    monkeypatch.setenv("MODEL_SOURCE", "local")
    monkeypatch.setenv("MODEL_PATH", str(path))
    with TestClient(serve.app) as api:
        yield api


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("value,label", [(0, "thu_nhap_thap"), (1, "thu_nhap_cao")])
def test_score_predicts_both_labels(client, value, label):
    response = client.post("/score", json={"features": [value] * 10})
    assert response.status_code == 200
    assert response.json() == {"prediction": value, "label": label}


@pytest.mark.parametrize("features", [[], [1] * 9, [1] * 11])
def test_score_rejects_wrong_length(client, features):
    assert client.post("/score", json={"features": features}).status_code == 400


def test_score_rejects_non_numeric_features(client):
    assert client.post("/score", json={"features": ["abc"] * 10}).status_code == 422


def test_score_rejects_non_finite_features(client):
    assert client.post("/score", json={"features": ["inf"] * 10}).status_code == 400


def test_cloud_startup_downloads_and_loads_model(tmp_path, monkeypatch):
    X = pd.DataFrame([[0.0] * 10, [1.0] * 10], columns=FEATURE_NAMES)
    model = DecisionTreeClassifier(random_state=42).fit(X, np.array([0, 1]))
    calls = []

    class FakeS3:
        def download_file(self, bucket, key, filename):
            calls.append((bucket, key))
            joblib.dump(model, filename)

    monkeypatch.setenv("MODEL_SOURCE", "cloud")
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "nested/model.joblib"))
    monkeypatch.setattr(serve.boto3, "client", lambda service: FakeS3())
    with TestClient(serve.app) as api:
        assert api.get("/healthz").status_code == 200
        assert api.post("/score", json={"features": [1] * 10}).json()["prediction"] == 1
    assert calls == [("test-bucket", "artifacts/current/model.joblib")]


def test_cloud_startup_requires_bucket(monkeypatch):
    monkeypatch.setenv("MODEL_SOURCE", "cloud")
    monkeypatch.delenv("ARTIFACT_BUCKET", raising=False)
    with pytest.raises(RuntimeError, match="ARTIFACT_BUCKET"):
        with TestClient(serve.app):
            pass


def test_failed_download_preserves_existing_model(tmp_path, monkeypatch):
    path = tmp_path / "model.joblib"
    path.write_bytes(b"previous-model")

    class FailingS3:
        def download_file(self, bucket, key, filename):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "GetObject")

    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    monkeypatch.setenv("MODEL_PATH", str(path))
    monkeypatch.setattr(serve.boto3, "client", lambda service: FailingS3())
    with pytest.raises(ClientError):
        serve.download_model()
    assert path.read_bytes() == b"previous-model"
