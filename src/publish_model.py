"""Publish a model to S3 only after validating its report's quality gate."""

import json
import argparse
import math
import os
from pathlib import Path
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.quality_gate import check_quality


def release_decision(s3, bucket: str, report: dict) -> dict:
    candidate = float(report["f1_score"])
    check_quality(candidate)
    try:
        response = s3.get_object(Bucket=bucket, Key="artifacts/current/report.json")
    except s3.exceptions.NoSuchKey:
        print("No previous report: first deployment allowed.")
        return {"deploy": True, "candidate_f1": candidate, "current_f1": None,
                "reason": "first_deployment"}
    # Permission/network failures propagate; they must never bypass this guard.
    with response["Body"] as body:
        previous = json.loads(body.read())
    current = float(previous["f1_score"])
    if not math.isfinite(current) or not 0 <= current <= 1:
        raise ValueError("Invalid F1 in currently deployed report")
    old_eval = previous.get("eval_data_sha256")
    new_eval = report.get("eval_data_sha256")
    if old_eval and new_eval and old_eval != new_eval:
        raise ValueError("Holdout changed: F1 reports cannot be compared safely")
    deploy = candidate >= current
    print(f"Regression guard: candidate F1={candidate:.6f}; current F1={current:.6f}; "
          f"{'ALLOW' if deploy else 'BLOCK - keep current model'}")
    return {"deploy": deploy, "candidate_f1": candidate, "current_f1": current,
            "reason": "not_worse" if deploy else "regression"}


def publish_model(bucket: str, model_path: Path, report_path: Path) -> bool:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    check_quality(float(report["f1_score"]))
    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    s3 = boto3.client("s3")
    decision = release_decision(s3, bucket, report)
    if not decision["deploy"]:
        return False
    s3.upload_file(str(model_path), bucket, "artifacts/current/model.joblib")
    s3.upload_file(str(report_path), bucket, "artifacts/current/report.json")
    print(f"Published approved model to s3://{bucket}/artifacts/current/model.joblib")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    bucket = os.environ.get("ARTIFACT_BUCKET")
    if not bucket:
        print("Set ARTIFACT_BUCKET before publishing.", file=sys.stderr)
        return 1
    try:
        report_path = Path("outputs/report.json")
        if args.check_only:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            check_quality(float(report["f1_score"]))
            decision = release_decision(boto3.client("s3"), bucket, report)
            Path("outputs/release-decision.json").write_text(
                json.dumps(decision, indent=2), encoding="utf-8")
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                    stream.write(f"deploy={str(decision['deploy']).lower()}\n")
        elif not publish_model(bucket, Path("models/model.joblib"), report_path):
            return 1
    except (ClientError, BotoCoreError, ValueError, KeyError, OSError, TypeError) as error:
        print(f"Publish failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
