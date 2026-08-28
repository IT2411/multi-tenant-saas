#!/usr/bin/env bash
set -e

# Run database migrations before starting the application worker
echo "[ENTRYPOINT] Applying pending database migrations via Alembic..."
alembic upgrade head

echo "[ENTRYPOINT] Booting application server..."
exec "$@"