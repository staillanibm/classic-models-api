# Domain events

The API publishes what it did, as facts, on Kafka. This is the contract a
consumer depends on — read it before writing one.

## The envelope

CloudEvents 1.0, JSON, one event per Kafka record.

```json
{
  "specversion": "1.0",
  "type": "com.sttlab.classicmodels.product.stock_changed.v1",
  "source": "/classic-models-api/catalog",
  "subject": "S12_1099",
  "id": "910a06a9-196a-4e6e-9761-96523f06778c",
  "time": "2026-08-31T05:34:18.565900Z",
  "datacontenttype": "application/json",
  "traceparent": "00-6978e938281bbf88ecdc098a9760aba7-e41103385e4871f7-01",
  "data": { "...": "per type, below" }
}
```

`subject` is the aggregate's id and is also the **partition key**.

`traceparent` is present when the change happened inside a traced request. It is
the W3C trace context of the span that raised the event, so an event joins the
request that caused it in the tracing backend.

### There is no actor

Deliberately. An event is a fact, not a command, and a consumer acts under its
own identity. A field naming who caused the change would have no consumer and
one obvious misuse: anyone able to write to the topic could name any actor and
have an agent act as them. A signed token is proof; a JSON field is not.

If you need causality, follow `traceparent`.

## Topics

One per aggregate, **not** one per event type — per type would lose the order
between `product.created` and `product.stock_changed` for the same product,
which is the one ordering a consumer actually needs.

| Topic | Carries | Partitions | Retention |
|---|---|---|---|
| `classic-models.catalog` | `product.*` | 3 | 7 days |
| `classic-models.sales` | `order.*` | 3 | 7 days |
| `classic-models.payments` | `payment.*` | 3 | 7 days |

Ordering holds **per entity**, because the partition key is the entity's id. It
does not hold across entities, and no consumer should assume it does.

The topics and the account that writes them are **not declared here**. Kafka is
administered centrally: the platform team owns topics and ACLs, in
`k8s-platform/kafka-topology/`. This API owns what an event *means* — the
contract on this page — and asks for the topic it needs.

Self-service, when it arrives, will not come from moving these files: it comes
from an event gateway that virtualises topics, and the developer portal that
socialises them, the way the REST APIs already are.

## The catalogue

Six types. Each has a consumer today — an event with none is a contract that has
to be honoured without anyone knowing why.

### `product.created.v1` → `classic-models.catalog`

Raised by `POST /catalog/v1/products/`. `subject` is the product code.

```json
{"productcode": "S12_1099", "productname": "1968 Ford Mustang",
 "productline": "Classic Cars", "quantityinstock": 68,
 "buyprice": "95.34", "msrp": "194.57"}
```

### `product.stock_changed.v1` → `classic-models.catalog`

Raised whenever stock moves — by an order line, or by someone editing the
product. `subject` is the product code.

```json
{"productcode": "S12_1099", "reason": "order:10103",
 "before": {"quantityinstock": 68}, "after": {"quantityinstock": 38}}
```

`reason` is `order:<ordernumber>` for demand and `manual-adjustment` for a
correction. **Consumers should treat them differently**: demand says something
about the future, a correction says someone fixed the books.

A third value: `delivery:<reorder-id>`, when a fulfilled reorder increases
stock. It is only accepted from a caller holding the narrow `restocker` role
(a `PATCH` sending `X-Stock-Change-Reason: delivery:<id>`, checked against
`^delivery:[\w-]{1,64}$`); anything else — a role without the header, or a
value not in that shape — falls back to `manual-adjustment`. See
`classic-models.procurement` below.

### `product.price_changed.v1` → `classic-models.catalog`

Raised by an update that changes `buyprice` or `msrp`.

```json
{"productcode": "S12_1099",
 "before": {"buyprice": "95.34", "msrp": "194.57"},
 "after":  {"buyprice": "99.00", "msrp": "199.00"}}
```

### `order.created.v1` → `classic-models.sales`

`subject` is the order number as a string.

```json
{"ordernumber": 10103, "customernumber": 363, "orderdate": "2026-08-31",
 "requireddate": "2026-09-10", "status": "In Process"}
```

### `order.status_changed.v1` → `classic-models.sales`

```json
{"ordernumber": 10103, "customernumber": 363,
 "before": {"status": "In Process"}, "after": {"status": "Shipped"}}
```

### `payment.recorded.v1` → `classic-models.payments`

`subject` is the **customer** number, not the cheque: a consumer chasing a debt
cares about one customer's payments in order, and a cheque number is not an
aggregate anyone reasons about.

```json
{"customernumber": 363, "checknumber": "HQ55W3", "paymentdate": "2026-08-31",
 "amount": "1200.00"}
```

## What is deliberately absent

**`orderline.created`.** Its only consumer would be an agent that does not
exist. It can be added when one does.

**Anything the API cannot know.** There is no `stock_out_risk_detected`: a
threshold is a consumer's judgement, and the API's job is to say stock went from
68 to 38. An agent decides what that means.

## Versioning

The version is part of the `type`. A field **added** is not a new version. A
field removed or renamed, or a meaning changed, becomes `.v2`, and both are
published while consumers move. Consumers must ignore fields they do not know.

## classic-models.procurement (not produced by this API)

A third topic exists alongside `catalog`/`sales`/`payments`, but this service
neither produces nor consumes it — `classic-models-api`'s own Kafka account
stays write-only on its own three topics, unchanged. `reorder.requested.v1`,
`reorder.confirmed.v1` and `reorder.rejected.v1` are raised and consumed
entirely within the supply agent (`classic-models-agent-flows`), which acts as
both requester and — simulating a supplier — the one who answers. The only
place this API is involved is the ordinary front door: a fulfilled reorder
reaches stock through the same `PATCH /catalog/v1/products/{productcode}/`
any other write does, under the `restocker` role, and it is `product.stock_changed`
that carries the fact — see `reason` above.

Documented here only so a reader of this file is not surprised: the estate has
a second, independent event stream that this API is not a party to.

## Delivery

**At least once.** A consumer must tolerate a repeat — the envelope's `id` is
assigned when the event happens, not when it is published, so a republished
event carries the same id and can be recognised.

No ordering across topics. No exactly-once. No compaction: these are facts, not
state, and a consumer that needs current state should read the API.

## How it is published

A **transactional outbox**, not a direct produce.

```
request → BEGIN
            change the row
            insert into outbox_event
          COMMIT
                        ↓
          relay ── polls ──→ Kafka ──→ marks published
```

An event commits **with** the change it describes, or neither does. Producing
directly from the request would allow both halves of the failure: a change with
no event, and an event for a change that was rolled back — the second is worse,
because a consumer then acts on something that never happened.

`events.emit.emit()` **raises** if called outside a transaction. That guard is
the design, not defensiveness.

The relay is a separate `Deployment` (`classic-models-api-outbox-relay`),
**single replica** — two would publish the same rows twice. It is
`python manage.py publish_outbox`; `--once` drains and exits, which is what a
test or a manual catch-up wants.

### Operating it

| | |
|---|---|
| Unpublished backlog | `select count(*) from outbox_event where published_at is null` |
| A row that keeps failing | `publish_attempts`, `last_error` on the same table |
| Credentials | `ExternalSecret` → `classic-models-api-kafka` (SCRAM password + cluster CA) |
| Account | `classic-models-api` — Write and Describe on `classic-models.` only, no Read |

The relay **crash-loops until migrations have run**. Harmless, Kubernetes
restarts it, but the first logs after an upgrade that adds a table will read
`Table 'classicmodels.outbox_event' doesn't exist`.

## A contract change came with this

`POST /catalog/v1/orderdetails/` now **decrements stock** and **refuses** a line
that exceeds what is on hand:

```
HTTP 400
{"quantityordered": ["Only 7933 of S10_1678 in stock; 99999 requested."]}
```

It used to accept anything and let stock go negative. The refusal names the
available quantity on purpose: a caller — an agent especially — needs the
difference between "retry with less" and "give up".

The decrement takes `SELECT ... FOR UPDATE` on the product row for the length of
the transaction, so two lines for the same product cannot both read 60 and both
write 45.
