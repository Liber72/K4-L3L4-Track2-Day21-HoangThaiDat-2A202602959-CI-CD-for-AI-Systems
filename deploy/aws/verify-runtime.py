"""Verify the EC2 identity, model download access, and denial of DVC data access."""

import sys

import boto3
from botocore.exceptions import ClientError


def main() -> int:
    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    print(f"Runtime identity: {identity['Arn']}")
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "income-day21-972243443873-use1"
    model = s3.head_object(Bucket=bucket, Key="artifacts/current/model.joblib")
    print(f"Model access allowed: {model['ContentLength']} bytes")
    try:
        s3.head_object(Bucket=bucket, Key="dvc/files/md5/60/97c9bf1219a011f64a7a594a7b617d")
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] == 403:
            print("DVC dataset access denied as intended.")
            return 0
        raise
    print("Unexpected dataset access: review the EC2 role.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
