import os

from .base import *  # noqa

DEBUG = False

# ALLOWED_HOSTS comes from base.py (env var, defaults to "*" if unset).

# Off by default: kubelet httpGet probes hit the pod over plain HTTP with no
# X-Forwarded-Proto header, so a forced redirect would fail health checks.
# Enable explicitly (SECURE_SSL_REDIRECT=1) if fronting with a proxy that
# always sets that header, including for probe traffic.
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "0") == "1"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
