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
# The access log carries the inbound W3C traceparent header, which Kong sets
# and propagates. Its trace id is the same one Tempo indexes, so a span in
# Grafana can find the access line it produced -- without it these lines have no
# link back to a trace at all. %({header}i)s logs a request header; gunicorn
# writes "-" when it is absent, so a direct call bypassing the gateway still
# produces a well-formed line.
#
# Appended at the end on purpose: the NCSA prefix stays byte-identical, so the
# parsers reading these lines are unaffected.
exec opentelemetry-instrument gunicorn config.wsgi:application \
  -c config/gunicorn.py \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" traceparent=%({traceparent}i)s' \
  --error-logfile -
