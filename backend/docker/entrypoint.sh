#!/bin/sh
set -e

echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head

if [ "${SEED_ON_STARTUP:-false}" = "true" ]; then
  echo "Seeding database..."
  python -m app.seed
fi

echo "Starting application: $*"
exec "$@"
