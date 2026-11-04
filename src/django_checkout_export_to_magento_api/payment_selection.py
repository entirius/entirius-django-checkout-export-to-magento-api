# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Which payment of a checkout order Magento hears about.

``payment_method`` is a list (``[voucher, payu]`` when a voucher covers part of the order) and entry ``[0]`` may be
the voucher, debited at order time. Magento gets the method that settles what the vouchers leave: the first that is
no voucher, else the first (vouchers covering the order). Same rule as ``django_checkout.domain.payment_selection``,
which the checkout release this module requires does not ship yet.
"""

from django_checkout.domain.dto.order import OrderData
from django_checkout.enums import PaymentProvider
from django_checkout.models import Order, PaymentIntent


def _first_settling(rows: list, is_voucher) -> object | None:  # noqa: ANN001
    return next((row for row in rows if not is_voucher(row)), rows[0] if rows else None)


def _is_voucher_intent(intent: PaymentIntent) -> bool:
    """Its method's provider decides; the code only without one (method removed, SET_NULL, or provider unset)."""
    provider = intent.method.provider if intent.method is not None else None
    if provider is not None:
        return str(provider) == PaymentProvider.VOUCHER
    return intent.code == PaymentProvider.VOUCHER


def settling_payment_intent(order: Order) -> PaymentIntent | None:
    """The intent of the method that settles the rest; the voucher's when the vouchers cover the order."""
    intents = list(order.payment_items.select_related("method").order_by("pk"))
    return _first_settling(intents, _is_voucher_intent)


def settling_payment_code(intent: PaymentIntent | None, order_data: OrderData) -> str | None:
    """The code of the settling ``intent``. A split part has no intent of its own: its code comes from the body."""
    if intent is not None:
        return intent.code
    entry = _first_settling(order_data.payment_method or [], lambda entry: entry.code == PaymentProvider.VOUCHER)
    return entry.code if entry else None
