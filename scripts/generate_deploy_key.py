"""Generate a local SSH key for the lab without printing the private key."""

from pathlib import Path
import subprocess


def main():
    path = Path(".local/aws/income-day21.pem").resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.with_suffix(".pem.pub").exists():
            raise RuntimeError("Existing key has no public-key file; refusing to overwrite it.")
        print(f"Using existing key: {path}")
        return
    subprocess.run(
        [
            "C:/Windows/System32/OpenSSH/ssh-keygen.exe", "-t", "ed25519",
            "-f", str(path), "-N", "", "-C", "income-day21-deploy",
        ],
        check=True,
    )
    print(f"Private key saved locally: {path}")


if __name__ == "__main__":
    main()
