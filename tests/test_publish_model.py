import json
import io

import pytest

from src import publish_model


@pytest.mark.parametrize("f1", [0.0, 0.64])
def test_rejected_model_never_touches_s3(tmp_path, monkeypatch, f1):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"f1_score": f1}), encoding="utf-8")

    def unexpected_client(service):
        pytest.fail("A rejected model must not access S3")

    monkeypatch.setattr(publish_model.boto3, "client", unexpected_client)
    with pytest.raises(ValueError, match="Release blocked"):
        publish_model.publish_model("test-bucket", tmp_path / "model.joblib", report)


def test_approved_model_and_report_are_uploaded(tmp_path, monkeypatch):
    model, report = tmp_path / "model.joblib", tmp_path / "report.json"
    model.write_bytes(b"candidate")
    report.write_text(json.dumps({"f1_score": 0.65}), encoding="utf-8")
    calls = []

    class FakeS3:
        def get_object(self, **kwargs):
            return {"Body": io.BytesIO(b'{"f1_score": 0.65}')}

        def upload_file(self, filename, bucket, key):
            calls.append((filename, bucket, key))

    monkeypatch.setattr(publish_model.boto3, "client", lambda service: FakeS3())
    publish_model.publish_model("test-bucket", model, report)
    assert calls == [
        (str(model), "test-bucket", "artifacts/current/model.joblib"),
        (str(report), "test-bucket", "artifacts/current/report.json"),
    ]
