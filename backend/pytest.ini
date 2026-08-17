#!/bin/sh
set -e

# Applying migrations here (rather than as a separate one-shot compose
# service) keeps `docker-compose up` to a single step per container and
# means every container that runs this image - the API, and the seed
# job - always starts from an up-to-date schema. `alembic upgrade head`
# is a no-op if the schema is already current, so running it from more
# than one container on startup is safe.
echo "[entrypoint] Waiting for database and applying migrations..."

# Postgres may not be accepting connections yet even though the
# container is "running" - the compose healthcheck handles the common
# case, but retry here too so this is robust even outside compose.
attempt=0
until alembic upgrade head; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 15 ]; then
    echo "[entrypoint] Migrations failed after $attempt attempts, giving up."
    exit 1
  fi
  echo "[entrypoint] Migration attempt $attempt failed, retrying in 2s..."
  sleep 2
done

echo "[entrypoint] Migrations applied. Starting: $*"
exec "$@"