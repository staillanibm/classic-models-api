#!/bin/bash
set -e

echo "Starting Classic Models API..."

# Display version information (DJANGO_SETTINGS_MODULE must be set in the
# container environment; defaults to config.settings.development otherwise)
echo "API Version: $(python -c "import django; django.setup(); from config.settings.base import get_version; print(get_version())")"

# Migrations run out-of-band (see scripts/migrate.sh, run as a one-off Job/step
# before rollout) to avoid multiple replicas racing to apply them concurrently.

GUNICORN_WORKERS=${GUNICORN_WORKERS:-3}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-30}

echo "Starting gunicorn..."
# -c config/gunicorn.py: hooks that aggregate Prometheus metrics across
# workers (see the module for the multiprocess details).
exec opentelemetry-instrument gunicorn config.wsgi:application \
  -c config/gunicorn.py \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
