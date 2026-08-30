"""The outbox, the stock commitment, and the events they produce.

What is worth testing here is not that a row appears — it is the three
properties the design rests on, each of which fails silently if it breaks:

- an event commits **with** its change, or not at all;
- stock cannot go negative, and a refusal says how much is available;
- an event is named for a business fact and carries before and after.
"""

from __future__ import annotations

import pytest
from django.db import transaction

from classicmodels.models import Product, ProductLine
from events import emit
from events.models import OutboxEvent
from events.stock import InsufficientStock, commit_stock


@pytest.fixture
def product(db) -> Product:
    line = ProductLine.objects.create(productline="Test Cars", textdescription="t")
    return Product.objects.create(
        productcode="S99_TEST",
        productname="Test Roadster",
        productline=line,
        productscale="1:18",
        productvendor="Lab Fixtures",
        productdescription="a test",
        quantityinstock=60,
        buyprice="50.00",
        msrp="99.00",
    )


class TestTheOutboxIsTransactional:
    @pytest.mark.django_db(transaction=True)
    def test_an_event_outside_a_transaction_is_refused(self) -> None:
        # The whole point of an outbox. An event that commits without its change
        # describes something that may never have happened, and a consumer
        # acting on it is acting on fiction.
        #
        # `transaction=True` on purpose: the ordinary `db` fixture wraps every
        # test in an atomic block, so the guard could never fire and the test
        # would pass by describing nothing.
        line = ProductLine.objects.create(productline="Guard", textdescription="t")
        unsaved = Product(
            productcode="S99_GUARD",
            productname="Guard",
            productline=line,
            productscale="1:18",
            productvendor="Lab Fixtures",
            productdescription="a test",
            quantityinstock=1,
            buyprice="1.00",
            msrp="2.00",
        )
        with pytest.raises(RuntimeError, match="outside a transaction"):
            emit.product_created(unsaved)

    def test_an_event_rolls_back_with_its_change(self, product) -> None:
        class Boom(Exception):
            pass

        with pytest.raises(Boom):
            with transaction.atomic():
                product.quantityinstock = 10
                product.save()
                emit.product_stock_changed(product, before=60, after=10, reason="test")
                raise Boom

        assert OutboxEvent.objects.count() == 0
        product.refresh_from_db()
        assert product.quantityinstock == 60


class TestCommitStock:
    def test_stock_is_taken_and_the_movement_is_announced(self, product) -> None:
        commit_stock(productcode="S99_TEST", quantity=30, ordernumber=10425)

        product.refresh_from_db()
        assert product.quantityinstock == 30

        event = OutboxEvent.objects.get()
        assert event.event_type.endswith("product.stock_changed.v1")
        assert event.partition_key == "S99_TEST"
        assert event.payload["data"]["before"] == {"quantityinstock": 60}
        assert event.payload["data"]["after"] == {"quantityinstock": 30}

    def test_ordering_more_than_there_is_refuses(self, product) -> None:
        with pytest.raises(InsufficientStock):
            commit_stock(productcode="S99_TEST", quantity=61, ordernumber=10425)

        product.refresh_from_db()
        assert product.quantityinstock == 60
        assert OutboxEvent.objects.count() == 0

    def test_the_refusal_says_how_much_is_available(self, product) -> None:
        # A caller — an agent especially — needs the difference between "retry
        # with less" and "give up". A bare rejection gives neither.
        with pytest.raises(InsufficientStock) as raised:
            commit_stock(productcode="S99_TEST", quantity=61, ordernumber=10425)
        assert "Only 60" in str(raised.value)

    def test_taking_exactly_what_is_left_is_allowed(self, product) -> None:
        commit_stock(productcode="S99_TEST", quantity=60, ordernumber=10425)
        product.refresh_from_db()
        assert product.quantityinstock == 0

    def test_the_movement_says_what_caused_it(self, product) -> None:
        # Demand and a correction are different signals. A reorder decision that
        # cannot tell them apart reorders against somebody fixing a typo.
        commit_stock(productcode="S99_TEST", quantity=5, ordernumber=10425)
        assert OutboxEvent.objects.get().payload["data"]["reason"] == "order:10425"


class TestTheEnvelope:
    def test_it_is_a_cloudevent(self, product) -> None:
        with transaction.atomic():
            emit.product_created(product)
        envelope = OutboxEvent.objects.get().payload
        assert envelope["specversion"] == "1.0"
        assert envelope["type"] == "com.sttlab.classicmodels.product.created.v1"
        assert envelope["subject"] == "S99_TEST"
        assert envelope["source"].startswith("/classic-models-api/")
        assert envelope["datacontenttype"] == "application/json"

    def test_it_carries_no_actor(self, product) -> None:
        # An event is a fact, not a command. A field naming who caused it would
        # have no consumer and one obvious misuse: anyone able to write to the
        # topic could name any actor and have an agent act as them.
        with transaction.atomic():
            emit.product_created(product)
        envelope = OutboxEvent.objects.get().payload
        assert "actorsub" not in envelope
        assert "actorazp" not in envelope

    def test_the_id_is_fixed_when_the_event_happens(self, product) -> None:
        # Not when it is published: a relay that retries must republish the same
        # event, so a consumer can recognise the repeat.
        with transaction.atomic():
            emit.product_created(product)
        row = OutboxEvent.objects.get()
        assert str(row.event_id) == row.payload["id"]

    def test_it_is_unpublished_until_the_relay_says_otherwise(self, product) -> None:
        with transaction.atomic():
            emit.product_created(product)
        assert OutboxEvent.objects.get().published_at is None
