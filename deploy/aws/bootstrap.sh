#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$HOME/income-app"
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip curl
mkdir -p "$APP_ROOT/src" "$APP_ROOT/models"
if [ ! -x "$APP_ROOT/.venv/bin/python" ]; then
  python3 -m venv "$APP_ROOT/.venv"
fi
"$APP_ROOT/.venv/bin/python" -m pip install -r "$APP_ROOT/requirements-serving.txt"
sudo install -m 0644 "$APP_ROOT/income-api.service" /etc/systemd/system/income-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now income-api
for attempt in $(seq 1 12); do
  if curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8080/healthz; then
    echo "API ready."
    exit 0
  fi
  sleep 5
done
sudo journalctl -u income-api -n 40 --no-pager
exit 1
