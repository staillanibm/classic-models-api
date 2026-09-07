"""Visibility into the outbox backlog.

The relay is optional (see `Values.kafka.enabled` in the Helm chart): with it
disabled, or merely stalled, `OutboxEvent` rows with no `published_at` pile up
forever by design -- the outbox's whole point is to never drop one. Nobody
should notice that until a dashboard says so, hence this gauge.
"""

from __future__ import annotations

from prometheus_client import Gauge

# multiprocess_mode="max": every gunicorn worker polls the same global count
# independently (see config/gunicorn.py), so their values agree modulo the
# poll interval. "max" collapses them into one series instead of one per pid.
outbox_unpublished_total = Gauge(
    "outbox_unpublished_total",
    "OutboxEvent rows with no published_at, i.e. waiting for the relay.",
    multiprocess_mode="max",
)


def refresh_outbox_unpublished_gauge() -> None:
    from django.db import connection

    from .models import OutboxEvent

    outbox_unpublished_total.set(
        OutboxEvent.objects.filter(published_at__isnull=True).count()
    )
    # A loop that never touches the connection between polls otherwise holds
    # it open across the interval, and MySQL closes it from under us.
    connection.close()
