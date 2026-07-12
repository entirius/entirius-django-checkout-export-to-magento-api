# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.core.exceptions import ObjectDoesNotExist
from django_checkout.models import Order, ShippingMethod


def order_find_by(order_pk: int | None = None, order_id: str | None = None, order_pretty_id: str | None = None):
    params_quantity = len({id(order_pk), id(order_id), id(order_pretty_id)} - {id(None)})
    if params_quantity != 1:
        raise ValueError(
            f"Can not find Order: exactly one of: order_pk={order_pk}, order_id={order_id} or order_pretty_id={order_pretty_id} must be set"
        )
    if order_pk is not None:
        return Order.objects.get(pk=order_pk)
    if order_id is not None:
        # ex: d68189e9-9625-416d-bba7-eae392c9b7b2
        if len(order_id) != 36:
            raise ValueError(f"Can not find Order, order_id={order_id} is not valid")
        return Order.objects.get(order_id=order_id)
    if order_pretty_id is not None:
        if len(order_pretty_id) != 10:
            raise ValueError(f"Can not find Order, order_pretty_id={order_pretty_id} is not valid")
        channel_pk, in_channel_id = Order.split_pretty_id(order_pretty_id)
        return Order.objects.get(channel__pk=channel_pk, in_channel_id=in_channel_id)
    raise Exception("Can not find Order")


def shipping_method_find_by(code: str, channel_idx: str = None) -> ShippingMethod | None:
    params = {}
    if channel_idx is not None:
        params["channel__idx"] = channel_idx
    try:
        return ShippingMethod.objects.get(code=code, **params)
    except ObjectDoesNotExist:
        return None
