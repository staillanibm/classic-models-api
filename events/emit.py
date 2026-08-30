"""Building a domain event and putting it in the outbox.

An event here is a **business fact the API performed**, named for what it means,
carrying the before and after of the fields that carry meaning. Not "a row
changed": that would make every consumer re-derive what mattered, and none of
them would agree.

Two things this deliberately does not do.

**It does not invent facts the API cannot know.** There is no
`stock_out_risk_detected` — that is an agent's judgement, with a threshold that
belongs to the agent. The API says stock went from 60 to 30.

**It does not carry who caused the change.** An event is a fact, not a command,
and a consumer acts under its own identity. A field naming an actor would have
no consumer and one obvious misuse: anyone able to write to the topic could name
any actor and have an agent act as them. A signed token is proof; a JSON field
is not. Causality is carried by `traceparent`, in the system that exists for it.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from django.db import transaction

from .models import OutboxEvent

#: Reverse-DNS, as CloudEvents asks. The version is part of the type: a field
#: removed or renamed becomes `.v2` and the two coexist while consumers move.
TYPE_PREFIX = "com.sttlab.classicmodels"

#: One topic per aggregate, not one per event type. Per type would lose the
#: order between `product.created` and `product.stock_changed` for the same
#: product, which is the one ordering a consumer actually needs.
TOPIC_CATALOG = "classic-models.catalog"
TOPIC_SALES = "classic-models.sales"
TOPIC_PAYMENTS = "classic-models.payments"


def _traceparent() -> str | None:
    """The current W3C trace context, if the request is being traced.

    This is what links an event back to the request that caused it. Reading it
    from the live span rather than a header means it is correct even when the
    event is raised deep in a call the request did not obviously make.
    """
    try:
        from opentelemetry import trace
    except ImportError:  # tracing is optional; an event is not
        return None

    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return None
    return f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-{ctx.trace_flags:02x}"


def emit(
    *,
    event_type: str,
    topic: str,
    subject: str,
    source: str,
    data: dict[str, Any],
) -> OutboxEvent:
    """Write one event to the outbox, inside the caller's transaction.

    Raises if called outside one. That is not defensiveness: an event committed
    without its change, or a change committed without its event, is precisely
    the failure the outbox exists to prevent, and it would show up as a
    consumer acting on something that never happened.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError(
            f"{event_type} was raised outside a transaction. An event must commit "
            "with the change it describes, or it describes something that may not exist."
        )

    envelope: dict[str, Any] = {
        "specversion": "1.0",
        "type": f"{TYPE_PREFIX}.{event_type}",
        "source": source,
        "subject": subject,
        "id": str(uuid.uuid4()),
        "time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "datacontenttype": "application/json",
        "data": data,
    }
    if traceparent := _traceparent():
        envelope["traceparent"] = traceparent

    return OutboxEvent.objects.create(
        event_id=envelope["id"],
        event_type=envelope["type"],
        topic=topic,
        partition_key=subject,
        payload=envelope,
    )


# --- the catalogue of events ----------------------------------------------
#
# Small, and each entry has a consumer today. An event with no consumer is a
# contract that has to be honoured without anyone knowing why.


def product_created(product) -> OutboxEvent:
    return emit(
        event_type="product.created.v1",
        topic=TOPIC_CATALOG,
        subject=product.productcode,
        source="/classic-models-api/catalog",
        data={
            "productcode": product.productcode,
            "productname": product.productname,
            "productline": str(product.productline_id),
            "quantityinstock": product.quantityinstock,
            "buyprice": str(product.buyprice),
            "msrp": str(product.msrp),
        },
    )


def product_stock_changed(product, *, before: int, after: int, reason: str) -> OutboxEvent:
    """Stock moved.

    `reason` says what moved it — an order line, or someone editing the product.
    A consumer deciding whether to reorder treats those differently: demand is a
    signal, a correction is not.
    """
    return emit(
        event_type="product.stock_changed.v1",
        topic=TOPIC_CATALOG,
        subject=product.productcode,
        source="/classic-models-api/catalog",
        data={
            "productcode": product.productcode,
            "reason": reason,
            "before": {"quantityinstock": before},
            "after": {"quantityinstock": after},
        },
    )


def product_price_changed(product, *, before: dict[str, str], after: dict[str, str]) -> OutboxEvent:
    return emit(
        event_type="product.price_changed.v1",
        topic=TOPIC_CATALOG,
        subject=product.productcode,
        source="/classic-models-api/catalog",
        data={"productcode": product.productcode, "before": before, "after": after},
    )


def order_created(order) -> OutboxEvent:
    return emit(
        event_type="order.created.v1",
        topic=TOPIC_SALES,
        subject=str(order.ordernumber),
        source="/classic-models-api/sales",
        data={
            "ordernumber": order.ordernumber,
            "customernumber": order.customernumber_id,
            "orderdate": str(order.orderdate),
            "requireddate": str(order.requireddate),
            "status": order.status,
        },
    )


def order_status_changed(order, *, before: str, after: str) -> OutboxEvent:
    return emit(
        event_type="order.status_changed.v1",
        topic=TOPIC_SALES,
        subject=str(order.ordernumber),
        source="/classic-models-api/sales",
        data={
            "ordernumber": order.ordernumber,
            "customernumber": order.customernumber_id,
            "before": {"status": before},
            "after": {"status": after},
        },
    )


def payment_recorded(payment) -> OutboxEvent:
    return emit(
        event_type="payment.recorded.v1",
        topic=TOPIC_PAYMENTS,
        # Keyed on the customer, not the cheque: a consumer chasing a debt cares
        # about one customer's payments in order, and the cheque number is not
        # an aggregate anyone reasons about.
        subject=str(payment.customernumber_id),
        source="/classic-models-api/payments",
        data={
            "customernumber": payment.customernumber_id,
            "checknumber": payment.checknumber,
            "paymentdate": str(payment.paymentdate),
            "amount": str(payment.amount),
        },
    )
