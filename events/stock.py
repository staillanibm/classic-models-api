"""Committing stock against an order line.

Until now `quantityinstock` was a number nobody moved: placing an order changed
no stock, so the catalog's figure described the day the database was seeded.
Nothing downstream could react to demand because demand left no trace.

Two things this has to get right, and both are easy to get wrong quietly.

**Concurrency.** Two lines for the same product, arriving together, both read 60
and both write 45 — the second overwrites the first and thirty units vanish from
the books. `select_for_update` makes the second wait for the first to commit.
The lock is taken on the product row and held for the length of the enclosing
transaction, which is short: read, subtract, write, emit.

**Refusal.** An order line for more than there is used to be accepted, and the
stock simply went negative. It is refused now.
"""

from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from classicmodels.models import Product

from . import emit


class InsufficientStock(serializers.ValidationError):
    """Raised as a validation error so DRF answers 400 with a usable body.

    A caller — and an agent especially — needs to know *how much* is available,
    not merely that it asked for too much: the difference is between retrying
    with a smaller quantity and giving up.
    """

    def __init__(self, productcode: str, requested: int, available: int) -> None:
        super().__init__(
            {
                "quantityordered": [
                    f"Only {available} of {productcode} in stock; {requested} requested."
                ]
            }
        )


@transaction.atomic
def commit_stock(*, productcode: str, quantity: int, ordernumber: int) -> None:
    """Take `quantity` off a product's stock, or refuse.

    Callers must not already hold the product row, and must not wrap this in an
    outer transaction that stays open long: the lock is released only at commit,
    and a long transaction here is a queue behind one popular product.
    """
    product = Product.objects.select_for_update().get(pk=productcode)

    before = product.quantityinstock
    if quantity > before:
        raise InsufficientStock(productcode, quantity, before)

    product.quantityinstock = before - quantity
    product.save(update_fields=["quantityinstock"])

    emit.product_stock_changed(
        product,
        before=before,
        after=product.quantityinstock,
        # Named so a consumer can tell demand from a correction. An agent
        # deciding whether to reorder treats them differently.
        reason=f"order:{ordernumber}",
    )
