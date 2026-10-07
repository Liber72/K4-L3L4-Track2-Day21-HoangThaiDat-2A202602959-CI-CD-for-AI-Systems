"""Publish a model to S3 only after validating its report's quality gate."""

import json
import os
from pathlib import Path
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.quality_gate import check_quality


def publish_model(bucket: str, model_path: Path, report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    check_quality(float(report["f1_score"]))
    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    s3 = boto3.client("s3")
    s3.upload_file(str(model_path), bucket, "artifacts/current/model.joblib")
    s3.upload_file(str(report_path), bucket, "artifacts/current/report.json")
    print(f"Published approved model to s3://{bucket}/artifacts/current/model.joblib")


def main() -> int:
    bucket = os.environ.get("ARTIFACT_BUCKET")
    if not bucket:
        print("Set ARTIFACT_BUCKET before publishing.", file=sys.stderr)
        return 1
    try:
        publish_model(bucket, Path("models/model.joblib"), Path("outputs/report.json"))
    except (ClientError, BotoCoreError, ValueError, KeyError, OSError, TypeError) as error:
        print(f"Publish failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
