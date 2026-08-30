"""The transactional outbox.

An event is written in the **same transaction** as the change it describes, and
a separate relay publishes it. The alternative — publish after `save()` — loses
the event if the process dies between the two, and an agent that never hears
about a stock movement is worse than one that hears late.

This is the estate's first Django-managed table. Every `classicmodels` model is
`managed = False`: those tables are the pre-existing schema and Django owns no
migrations for them. This one it does own, deliberately, because an outbox has
to live in the same database as the data to share its transaction — that is the
entire point.
"""

from __future__ import annotations

from django.db import models


class OutboxEvent(models.Model):
    """One domain event, waiting to be published.

    Rows are kept after publication rather than deleted: `published_at` is the
    record of what left and when, and pruning it is a scheduled job's business,
    not the write path's.
    """

    id = models.BigAutoField(primary_key=True)

    #: The CloudEvents `id`. Generated here so the identity of an event is fixed
    #: at the moment it happened, not at the moment it was published — a relay
    #: that retries must republish the same event, not a new one.
    event_id = models.UUIDField(unique=True)

    #: The CloudEvents `type`, version included: `…product.stock_changed.v1`.
    event_type = models.CharField(max_length=200)

    #: Kafka topic. One per aggregate, so ordering is preserved per entity.
    topic = models.CharField(max_length=100)

    #: The partition key: the aggregate's own identifier. Every event about one
    #: product lands on one partition, which is the only ordering a consumer
    #: needs.
    partition_key = models.CharField(max_length=100)

    #: The complete CloudEvent, envelope and all, as it will be published.
    payload = models.JSONField()

    occurred_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    #: Counted so a poison event is visible rather than retried for ever.
    publish_attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        db_table = "outbox_event"
        indexes = [
            # The relay's only query: unpublished, oldest first. Partial indexes
            # are not portable across the backends this runs on, so the index
            # carries both columns and the planner uses the leading one.
            models.Index(fields=["published_at", "id"], name="outbox_unpublished_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.partition_key}"
