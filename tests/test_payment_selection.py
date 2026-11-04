# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Magento hears about the payment that settles what the vouchers leave, not entry ``[0]``.

``payment_method`` is a list since checkout 9.0.0: the order export read ``payment_method.code`` off the list (an
AttributeError on every order) and the intent's transaction id off the first intent, the voucher's for
``[voucher, payu]``. The invoice export fetched the order's one intent with ``get()``, which fails on two, and its
command listed an order once per COMPLETE intent.
"""

from types import SimpleNamespace

import pytest
from django.core.management import call_command
from django_checkout.enums import OrderStatus, PaymentIntentStatus, PaymentProvider
from django_checkout.models import Channel, Order, PaymentIntent, PaymentMethod

from django_checkout_export_to_magento_api.models import OrderInMagento
from django_checkout_export_to_magento_api.payment_selection import settling_payment_code, settling_payment_intent
from django_checkout_export_to_magento_api.tasks import export_order_payment_to_magento

COMPLETE, PENDING = PaymentIntentStatus.COMPLETE, PaymentIntentStatus.PENDING
# What the export reads off OrderData: the body's entries, in the order the client sent them.
BODY = SimpleNamespace(payment_method=[SimpleNamespace(code="voucher"), SimpleNamespace(code="payu")])


@pytest.fixture
def channel(db):
    from django_regional.models import Country, Currency, Language

    if not Country.objects.filter(iso2="PL").exists():
        Country.objects.bulk_create([Country(iso2="PL", iso3="POL", name_en="Poland", name_pl="Polska")])
    return Channel.objects.create(
        idx="test-channel",
        label="Test Channel",
        min_order_price=0,
        default_language=Language.objects.get_or_create(iso2="en", defaults={"iso3": "eng", "name_en": "English"})[0],
        default_currency=Currency.objects.get_or_create(iso3="EUR", defaults={"name_en": "Euro"})[0],
        default_country=Country.objects.get(iso2="PL"),
    )


@pytest.fixture
def order(channel):
    return Order.objects.create(channel=channel, order_body={}, order_status=OrderStatus.UNPAID)


def _intent(order, code, provider, status):
    method = PaymentMethod.objects.create(channel=order.channel, code=code, provider=provider) if provider else None
    return PaymentIntent.objects.create(
        order=order, code=code, method=method, payment_status=status, amount="10.00", external_order_id=f"{code}-1"
    )


@pytest.mark.django_db
class TestTheSettlingPayment:
    def test_a_gateway_after_a_voucher(self, order):
        _intent(order, "voucher", PaymentProvider.VOUCHER, COMPLETE)
        payu = _intent(order, "payu", PaymentProvider.PAYU, PENDING)

        assert settling_payment_intent(order) == payu
        assert settling_payment_code(order, BODY) == "payu"

    def test_a_voucher_method_named_otherwise_is_still_a_voucher(self, order):
        _intent(order, "gift-card", PaymentProvider.VOUCHER, COMPLETE)
        _intent(order, "payu", PaymentProvider.PAYU, PENDING)

        assert settling_payment_code(order, BODY) == "payu"

    def test_a_removed_voucher_method_is_told_by_its_code(self, order):
        _intent(order, "voucher", None, COMPLETE)
        _intent(order, "payu", PaymentProvider.PAYU, PENDING)

        assert settling_payment_code(order, BODY) == "payu"

    def test_full_voucher_coverage_is_the_voucher(self, order):
        voucher = _intent(order, "voucher", PaymentProvider.VOUCHER, COMPLETE)

        assert settling_payment_intent(order) == voucher

    def test_an_order_without_intents_reads_the_body(self, order):
        """A split part is created without payment processing."""
        assert settling_payment_intent(order) is None
        assert settling_payment_code(order, BODY) == "payu"


@pytest.mark.django_db
class TestTheInvoice:
    def test_waits_for_the_gateway_next_to_a_debited_voucher(self, order):
        _intent(order, "voucher", PaymentProvider.VOUCHER, COMPLETE)
        _intent(order, "payu", PaymentProvider.PAYU, PENDING)

        export_order_payment_to_magento(order_pk=order.pk)  # returns before Magento: no OrderInMagento needed

    def test_the_command_exports_an_order_once(self, order, monkeypatch):
        _intent(order, "voucher", PaymentProvider.VOUCHER, COMPLETE)
        _intent(order, "payu", PaymentProvider.PAYU, COMPLETE)
        OrderInMagento.objects.create(
            checkout_order=order, success=True, magento_url="https://magento.example.invalid", request={}
        )
        exported = []
        command = "django_checkout_export_to_magento_api.management.commands.export-orders-payment-to-magento"
        monkeypatch.setattr(f"{command}.export_order_payment_to_magento", lambda order_pk: exported.append(order_pk))

        call_command("export-orders-payment-to-magento", order.channel.idx)

        assert exported == [order.pk]
