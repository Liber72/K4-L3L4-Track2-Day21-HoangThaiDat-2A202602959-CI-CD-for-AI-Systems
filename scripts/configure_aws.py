"""Translate STORAGE_CREDENTIALS JSON into a private credentials file for CI."""

import json
import os
from pathlib import Path
import tempfile


def main():
    raw = os.environ.get("STORAGE_CREDENTIALS")
    if not raw:
        raise SystemExit("Set the STORAGE_CREDENTIALS repository secret before running CI.")
    credentials = json.loads(raw)
    fields = {}
    for key in ("aws_access_key_id", "aws_secret_access_key", "aws_session_token"):
        value = credentials.get(key)
        if key != "aws_session_token" and not value:
            raise SystemExit(f"STORAGE_CREDENTIALS requires {key}.")
        if value is not None:
            if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n"):
                raise SystemExit(f"Invalid credential field: {key}")
            fields[key] = value
    descriptor, filename = tempfile.mkstemp(prefix="income-aws-", dir=os.environ["RUNNER_TEMP"])
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("[default]\n")
        for key, value in fields.items():
            stream.write(f"{key} = {value}\n")
    Path(filename).chmod(0o600)
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as stream:
        stream.write(f"AWS_SHARED_CREDENTIALS_FILE={filename}\n")
    print("AWS credentials configured for this job.")


if __name__ == "__main__":
    main()
