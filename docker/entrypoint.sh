#!/bin/sh
set -eu

python <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
timeout = int(os.getenv("POSTGRES_WAIT_TIMEOUT", "60"))
deadline = time.time() + timeout

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        if time.time() > deadline:
            raise SystemExit(f"Timed out waiting for Postgres at {host}:{port}")
        time.sleep(1)
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
