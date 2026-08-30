"""Publish the outbox to Kafka.

A separate process, not a thread inside gunicorn: a relay that dies must not
take the API with it, and an API that is restarted must not interrupt a publish
mid-batch. It also means the relay can be scaled, paused or rolled back on its
own, which is what you want of the component that talks to a broker.

Delivery is **at least once**. The publish and the mark-as-published cannot be
one atomic act across two systems, so a crash between them republishes. Every
event carries a stable CloudEvents `id`, generated when the event happened
rather than when it was sent, so a consumer can recognise the repeat. Consumers
must be idempotent; that is the contract, and it is cheaper than the alternative
of losing events.
"""

from __future__ import annotations

import json
import signal
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from events.models import OutboxEvent


class Command(BaseCommand):
    help = "Publish unpublished outbox events to Kafka, then keep watching."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--poll-seconds", type=float, default=1.0)
        parser.add_argument(
            "--once",
            action="store_true",
            help="Drain what is pending and exit. For tests and for a one-off catch-up.",
        )

    def handle(self, *args, **options) -> None:
        producer = self._producer()
        stopping = False

        def stop(_signum, _frame):
            # Finish the batch in flight rather than dropping it: the events are
            # already committed, and exiting mid-batch only means republishing
            # them later.
            nonlocal stopping
            stopping = True
            self.stdout.write("stopping after this batch")

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        while not stopping:
            sent = self._drain(producer, options["batch_size"])
            if options["once"] and sent == 0:
                break
            if sent == 0:
                time.sleep(options["poll_seconds"])

        producer.flush(10)

    def _producer(self):
        from confluent_kafka import Producer

        conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "SCRAM-SHA-512",
            "sasl.username": settings.KAFKA_USERNAME,
            "sasl.password": settings.KAFKA_PASSWORD,
            "ssl.ca.location": settings.KAFKA_CA_LOCATION,
            # The broker must have the record on disk and replicated before this
            # counts as sent. Anything weaker turns "at least once" into "most of
            # the time", which is the same as no guarantee for anyone reasoning
            # about it.
            "acks": "all",
            "enable.idempotence": True,
            "client.id": "classic-models-api-outbox",
        }
        return Producer(conf)

    def _drain(self, producer, batch_size: int) -> int:
        pending = list(
            OutboxEvent.objects.filter(published_at__isnull=True).order_by("id")[:batch_size]
        )
        if not pending:
            return 0

        delivered: list[OutboxEvent] = []
        failed: list[tuple[OutboxEvent, str]] = []

        def report(err, msg, event=None):
            if err is None:
                delivered.append(event)
            else:
                failed.append((event, str(err)))

        for event in pending:
            producer.produce(
                topic=event.topic,
                # The partition key is the aggregate id, so every event about
                # one entity lands on one partition and arrives in order.
                key=event.partition_key.encode(),
                value=json.dumps(event.payload).encode(),
                on_delivery=lambda err, msg, e=event: report(err, msg, e),
            )
        producer.flush(30)

        now = timezone.now()
        with transaction.atomic():
            if delivered:
                OutboxEvent.objects.filter(id__in=[e.id for e in delivered]).update(
                    published_at=now
                )
            for event, error in failed:
                # Counted rather than retried blindly: an event that keeps
                # failing is visible in the table instead of spinning silently.
                OutboxEvent.objects.filter(id=event.id).update(
                    publish_attempts=event.publish_attempts + 1, last_error=error[:500]
                )

        if failed:
            self.stderr.write(f"{len(failed)} event(s) failed to publish; first: {failed[0][1]}")
        return len(delivered)
