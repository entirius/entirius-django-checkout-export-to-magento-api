# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""An order a voucher paid for, in whole or in part, reaches Magento with its sums intact.

Checkout takes the voucher off the order total and leaves the lines at their sold price, so the export's amount
check (lines + shipping - discounts = total) failed on every such order. Magento Open Source has no gift card or
split tender: the voucher goes as an order discount laid on the lines (the invoice sums line discounts), described
by its masked code, and the payment is the method that settles the rest, or ``free`` when nothing is left.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from django_checkout.enums import ItemStatus, OrderStatus, PaymentIntentStatus, PaymentProvider
from django_checkout.models import Channel, Order, PaymentIntent, PaymentMethod
from magento2_sdk.services import OrderService

from django_checkout_export_to_magento_api.models import Channel as MagentoChannel
from django_checkout_export_to_magento_api.models import OrderInMagento
from django_checkout_export_to_magento_api.tasks import export_checkout_order_to_magento

D = Decimal


@pytest.fixture
def channel(db):
    from django_regional.models import Country, Currency, Language

    if not Country.objects.filter(iso2="PL").exists():
        Country.objects.bulk_create([Country(iso2="PL", iso3="POL", name_en="Poland", name_pl="Polska")])
    MagentoChannel.objects.create(idx="test-channel", label="Test Channel", default_magento_store_id="1")
    return Channel.objects.create(
        idx="test-channel",
        label="Test Channel",
        min_order_price=0,
        default_language=Language.objects.get_or_create(iso2="en", defaults={"iso3": "eng", "name_en": "English"})[0],
        default_currency=Currency.objects.get_or_create(iso3="EUR", defaults={"name_en": "Euro"})[0],
        default_country=Country.objects.get(iso2="PL"),
    )


@pytest.fixture
def sent(monkeypatch):
    """The entity the export hands Magento; Magento answers with a created order."""
    entities = []

    def create_order(self, entity):
        entities.append(entity["entity"])
        return {"entity_id": 7, "increment_id": "1"}

    monkeypatch.setattr(OrderService, "create_order", create_order)
    return entities


NO_DISCOUNT = D("0.00")


def _line(sku, unit_price, quantity=1, discount=NO_DISCOUNT):
    """A 23% VAT line at its sold gross price; ``discount`` is the row's discount code share."""
    unit_tax = (unit_price - unit_price / D("1.23")).quantize(D(".01"))
    return SimpleNamespace(
        sku=sku,
        name=sku,
        extra=None,
        tax_rate=D("0.23"),
        base_unit_price=unit_price - unit_tax,
        unit_price=unit_price,
        unit_tax_amount=unit_tax,
        quantity=quantity,
        discount_amount=discount,
        discount_percent=None,
    )


def _address():
    return SimpleNamespace(
        city="Gdansk",
        country_code="pl",
        email="buyer@example.invalid",
        firstname="Jan",
        lastname="Test",
        postcode="80-001",
        street="Testowa 1",
        dialling_code="+48",
        telephone="500000000",
        company=None,
        tax_id=None,
    )


def _order_data(lines, *, shipping, total, total_tax, voucher=None, discounts=(), payments=("payu",), pay_code=None):
    return SimpleNamespace(
        cart=SimpleNamespace(items=lines, discounts=list(discounts), voucher_amount_applied=voucher),
        addresses=SimpleNamespace(billing_address=_address(), shipping_address=_address()),
        shipping_method=SimpleNamespace(
            code="courier",
            name="Courier",
            delivery_point=None,
            unit_price_netto=(shipping / D("1.23")).quantize(D(".01")),
            total_price=shipping,
            tax_rate=D("0.23"),
        ),
        payment_method=[
            SimpleNamespace(code=code, pay_code=pay_code if code == "voucher" else None) for code in payments
        ],
        fee_price=D("0"),
        comment="",
        total=total,
        total_tax=total_tax,
        language_code="en",
        currency_code="eur",
    )


def _discount(code, amount):
    return SimpleNamespace(code=code, status=ItemStatus.VALID, price_discount=amount, percent_discount=0)


def _order(channel, monkeypatch, data, intents):
    order = Order.objects.create(channel=channel, order_body={}, order_status=OrderStatus.UNPAID)
    monkeypatch.setattr(Order, "as_data", property(lambda self: data))
    for code, provider in intents:
        method = PaymentMethod.objects.create(channel=channel, code=code, provider=provider)
        PaymentIntent.objects.create(
            order=order,
            code=code,
            method=method,
            payment_status=PaymentIntentStatus.COMPLETE,
            amount="1.00",
            external_order_id=f"{code}-tx",
        )
    return order


def _export(order):
    export_checkout_order_to_magento(channel_idx="test-channel", order_pk=order.pk)
    return OrderInMagento.objects.get(checkout_order=order, success=True)


def _row_discounts(entity):
    return sum(D(str(item["discount_amount"])) for item in entity["items"])


VOUCHER = ("voucher", PaymentProvider.VOUCHER)
PAYU = ("payu", PaymentProvider.PAYU)


@pytest.mark.django_db
class TestAVoucherInMagento:
    def test_an_order_without_a_voucher_is_sent_as_before(self, channel, monkeypatch, sent):
        data = _order_data([_line("A", D("100.00"))], shipping=D("10.00"), total=D("110.00"), total_tax=D("20.57"))
        _export(_order(channel, monkeypatch, data, [PAYU]))

        entity = sent[0]
        assert D(str(entity["grand_total"])) == D("110.00")
        assert D(str(entity["discount_amount"])) == 0
        assert entity["discount_description"] == ""
        assert entity["payment"]["method"] == "banktransfer"

    def test_a_partial_voucher_is_a_discount_and_the_gateway_pays_the_rest(self, channel, monkeypatch, sent):
        data = _order_data(
            [_line("A", D("60.00")), _line("B", D("20.00"), quantity=2)],
            shipping=D("10.00"),
            total=D("80.00"),
            total_tax=D("14.96"),
            voucher=D("30.00"),
            payments=("voucher", "payu"),
            pay_code="26WT********",
        )
        _export(_order(channel, monkeypatch, data, [VOUCHER, PAYU]))

        entity = sent[0]
        assert D(str(entity["grand_total"])) == D("80.00")
        assert D(str(entity["discount_amount"])) == D("-30.00")
        # Magento's invoice sums the line discounts: they carry the voucher, split by what each line costs.
        assert _row_discounts(entity) == D("30.00")
        assert [D(str(item["discount_amount"])) for item in entity["items"]] == [D("18.00"), D("12.00")]
        assert [item["base_discount_amount"] for item in entity["items"]] == [
            item["discount_amount"] for item in entity["items"]
        ]
        assert entity["discount_description"] == "Voucher 26WT********"
        assert entity["coupon_code"] == ""
        assert entity["payment"]["additional_information"] == {"transaction_id": "payu-tx"}

    def test_a_voucher_covering_the_order_is_paid_free(self, channel, monkeypatch, sent):
        data = _order_data(
            [_line("A", D("100.00"))],
            shipping=D("0.00"),
            total=D("0.00"),
            total_tax=D("0.00"),
            voucher=D("100.00"),
            payments=("voucher",),
        )
        _export(_order(channel, monkeypatch, data, [VOUCHER]))

        entity = sent[0]
        assert D(str(entity["grand_total"])) == 0
        assert D(str(entity["discount_amount"])) == D("-100.00")
        assert entity["discount_description"] == "Voucher"
        assert entity["payment"]["method"] == "free"

    def test_a_voucher_larger_than_the_cart_counts_what_it_took_off(self, channel, monkeypatch, sent):
        """Checkout 9.0.0 reports the voucher module's figure, which may exceed the cart; only the lines lost it."""
        data = _order_data(
            [_line("A", D("100.00"))],
            shipping=D("0.00"),
            total=D("0.00"),
            total_tax=D("0.00"),
            voucher=D("150.00"),
            payments=("voucher",),
        )
        _export(_order(channel, monkeypatch, data, [VOUCHER]))

        assert D(str(sent[0]["discount_amount"])) == D("-100.00")

    def test_a_voucher_next_to_a_discount_code(self, channel, monkeypatch, sent):
        data = _order_data(
            [_line("A", D("100.00"), discount=D("10.00"))],
            shipping=D("10.00"),
            total=D("70.00"),
            total_tax=D("13.10"),
            voucher=D("30.00"),
            discounts=[_discount("PROMO10", D("10.00"))],
            payments=("voucher", "payu"),
            pay_code="26WT********,9F56********",
        )
        _export(_order(channel, monkeypatch, data, [VOUCHER, PAYU]))

        entity = sent[0]
        assert D(str(entity["grand_total"])) == D("70.00")
        assert D(str(entity["discount_amount"])) == D("-40.00")
        assert entity["coupon_code"] == "PROMO10"
        assert entity["discount_description"] == "PROMO10 Voucher 26WT********,9F56********"

    def test_a_raw_voucher_code_never_reaches_magento(self, channel, monkeypatch, sent):
        data = _order_data(
            [_line("A", D("100.00"))],
            shipping=D("10.00"),
            total=D("80.00"),
            total_tax=D("15.00"),
            voucher=D("30.00"),
            payments=("voucher", "payu"),
            pay_code="26WTY3QY2WGN:1234",
        )
        _export(_order(channel, monkeypatch, data, [VOUCHER, PAYU]))

        assert "26WTY3QY2WGN" not in str(sent[0])
        assert sent[0]["discount_description"] == "Voucher"

    def test_a_discount_code_rest_moves_the_base_discount_too(self, channel, monkeypatch, sent):
        """The cent the lines miss of the code's amount lands on one line; its base value follows."""
        data = _order_data(
            [_line("A", D("100.00"), discount=D("9.00"))],
            shipping=D("10.00"),
            total=D("100.00"),
            total_tax=D("18.70"),
            discounts=[_discount("PROMO10", D("10.00"))],
        )
        _export(_order(channel, monkeypatch, data, [PAYU]))

        item = sent[0]["items"][0]
        assert D(str(item["discount_amount"])) == D("10.00")
        assert item["base_discount_amount"] == item["discount_amount"]

    def test_the_voucher_is_measured_after_the_discount_code_fix_up(self, channel, monkeypatch, sent):
        """The code's missing cent moves onto the line first; the voucher then covers what is left, never more."""
        data = _order_data(
            [_line("A", D("100.00"), discount=D("9.00"))],
            shipping=D("0.00"),
            total=D("0.00"),
            total_tax=D("0.00"),
            voucher=D("91.00"),
            discounts=[_discount("PROMO10", D("10.00"))],
            payments=("voucher",),
        )
        _export(_order(channel, monkeypatch, data, [VOUCHER]))

        item = sent[0]["items"][0]
        assert D(str(item["discount_amount"])) == D("100.00")
        assert D(str(sent[0]["grand_total"])) == 0

    def test_another_method_s_masked_code_is_not_a_voucher(self, channel, monkeypatch, sent):
        data = _order_data(
            [_line("A", D("100.00"))],
            shipping=D("10.00"),
            total=D("80.00"),
            total_tax=D("15.00"),
            voucher=D("30.00"),
            payments=("voucher", "payu"),
            pay_code="26WT********",
        )
        data.payment_method[1].pay_code = "****1234"
        _export(_order(channel, monkeypatch, data, [VOUCHER, PAYU]))

        assert sent[0]["discount_description"] == "Voucher 26WT********"
