# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import logging
from decimal import Decimal

from django_checkout.domain.customs_threshold import ABOVE_THRESHOLD
from django_checkout.domain.dto.address import AddressData
from django_checkout.domain.dto.discount import DiscountData, ValidatedDiscountData
from django_checkout.domain.dto.item import ItemData, ValidatedItemData
from django_checkout.domain.dto.order import OrderData
from django_checkout.enums import ItemStatus
from django_checkout.models import Order as CheckoutOrder
from django_checkout.models import ShippingMethod
from django_checkout.models.stock import remove_quantities_for_reservation_object
from django_checkout.models.stock_reservation import StockReservation
from magento2_sdk.client import Client
from magento2_sdk.dto.address import BillingAddress, ShippingAddress
from magento2_sdk.dto.extension_attributes import (
    ExtensionAttributes,
    Shipping,
    ShippingAssignment,
    ShippingTotal,
    StatusHistories,
)
from magento2_sdk.dto.item import Item
from magento2_sdk.dto.order import Order, OrderState, OrderStatus
from magento2_sdk.dto.payment import Payment
from magento2_sdk.services import OrderService
from magento2_sdk.utils import DecimalEncoder

from django_checkout_export_to_magento_api import settings
from django_checkout_export_to_magento_api.models import Channel, OrderInMagento
from django_checkout_export_to_magento_api.repository import order_find_by, shipping_method_find_by

from ..bi import ExportOrderToMagentoEvent

MAGENTO_URL = settings.MAGENTO2_URL_FOR_CHECKOUT_EXPORT
MAGENTO_TOKEN = settings.MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT

logger = logging.getLogger(__name__)
logger_process = logging.getLogger("process")


def map_items(items_checkout: list[ItemData | ValidatedItemData], checkout_order: Order) -> list[Item]:
    items = []

    for i in items_checkout:
        additional_data = {}
        if hasattr(i, "extra") and i.extra:
            additional_data = i.extra if i.extra else {}

        tax_rate = Decimal(i.tax_rate) if i.tax_rate is not None else Decimal("0")
        # tax_value = Decimal(1 + tax_rate)
        original_price_net = Decimal(i.base_unit_price).quantize(Decimal(".0001"))
        price_net = Decimal(i.unit_price - i.unit_tax_amount)
        price_gross = i.unit_price

        if additional_data:
            additional_data = json.dumps(additional_data, ensure_ascii=False)

        item = Item(
            sku=str(i.sku),
            name=str(i.name),
            additional_data=additional_data if additional_data else "",
            qty_ordered=i.quantity,
            price=price_net,
            original_price=original_price_net,
            tax_amount=Decimal(i.unit_tax_amount) * Decimal(i.quantity),
            tax_percent=tax_rate * 100,
            price_incl_tax=price_gross,
            discount_amount=i.discount_amount,
            discount_percent=Decimal(i.discount_percent) if i.discount_percent is not None else Decimal("0"),
        )
        items.append(item)
    return items


def map_address(address: AddressData) -> (BillingAddress, ShippingAddress):
    billing_address = BillingAddress(
        city=address.billing_address.city if address.billing_address.city else "",
        country_id=address.billing_address.country_code.upper(),
        email=address.billing_address.email,
        firstname=address.billing_address.firstname if address.billing_address.firstname else "",
        lastname=address.billing_address.lastname if address.billing_address.lastname else "",
        postcode=address.billing_address.postcode if address.billing_address.postcode else "",
        street=[address.billing_address.street if address.billing_address.street else ""],
        telephone=address.billing_address.dialling_code + address.billing_address.telephone
        if address.billing_address.telephone
        else "",
        company=address.billing_address.company if address.billing_address.company is not None else None,
        vat_id=address.billing_address.tax_id if address.billing_address.tax_id is not None else None,
    )
    shipping_address = ShippingAddress(
        city=address.shipping_address.city if hasattr(address.shipping_address, "city") else "",
        country_id=address.shipping_address.country_code.upper(),
        email=address.shipping_address.email,
        firstname=address.shipping_address.firstname if hasattr(address.shipping_address, "firstname") else "",
        lastname=address.shipping_address.lastname if hasattr(address.shipping_address, "lastname") else "",
        postcode=address.shipping_address.postcode if hasattr(address.shipping_address, "postcode") else "",
        street=[address.shipping_address.street if hasattr(address.shipping_address, "street") else ""],
        telephone=address.shipping_address.dialling_code + address.shipping_address.telephone
        if hasattr(address.shipping_address, "telephone")
        else "",
    )
    return billing_address, shipping_address


def map_discount_codes(discounts: list[DiscountData | ValidatedDiscountData]) -> str:
    codes = []
    for discount in discounts:
        if discount.status == ItemStatus.VALID:
            codes.append(discount.code)

    if len(codes) == 0:
        return ""
    else:
        return " ".join(codes)


def export_checkout_order_to_magento(
    channel_idx, order_pk: int | None = None, order_id: str | None = None, order_pretty_id: str | None = None
):
    """
    exactly one of: order_pk, order_id or order_pretty_id must be set
    """
    bev = ExportOrderToMagentoEvent(
        order_pk=order_pk, order_id=order_id, order_pretty_id=order_pretty_id, is_ongoing_event=True
    )
    report = {
        "is_order_found": False,
        "is_shipping_collected": False,
        "is_payment_collected": False,
        "is_discount_collected": False,
        "is_order_entity_saved": False,
        "is_request_done": False,
        "is_request_done_with_success": False,
        "magento_response": None,
    }
    try:
        checkout_order: CheckoutOrder = order_find_by(order_pk, order_id, order_pretty_id)
        order_id = checkout_order.order_id
        order_pretty_id = checkout_order.pretty_id
        bev.set_details(
            details={
                "order_pk": checkout_order.pk,
                "order_id": checkout_order.order_id,
                "order_pretty_id": checkout_order.pretty_id,
            }
        )
        report["is_order_found"] = True
        order_data: OrderData = checkout_order.as_data
        items = map_items(order_data.cart.items, checkout_order)
        billing_address, shipping_address = map_address(order_data.addresses)
        shipping_method = shipping_method_find_by(order_data.shipping_method.code, channel_idx)

        if order_data.shipping_method.code in settings.MAPPING_SHIPPING_METHODS.keys():
            magento_shipping_method = settings.MAPPING_SHIPPING_METHODS[order_data.shipping_method.code]
        else:
            magento_shipping_method = settings.MAPPING_SHIPPING_METHODS["default_shipping_magento_code"]

        ext_attr = ExtensionAttributes(
            shipping_assignments=[
                ShippingAssignment(shipping=Shipping(address=shipping_address, method=magento_shipping_method))
            ],
        )

        if (
            shipping_method
            and shipping_method.method_type == ShippingMethod.MethodType.INPOST
            and order_data.shipping_method.delivery_point
        ):
            ext_attr.delivery_point_code = (
                order_data.shipping_method.delivery_point.code
                if hasattr(order_data.shipping_method.delivery_point, "code")
                else order_data.shipping_method.delivery_point.name
            )
            ext_attr.delivery_point_name = order_data.shipping_method.delivery_point.name
            ext_attr.delivery_point_address = order_data.shipping_method.delivery_point.address
            ext_attr.delivery_point_city = order_data.shipping_method.delivery_point.city
            ext_attr.delivery_point_postcode = order_data.shipping_method.delivery_point.postcode

        shipping_amount_without_tax = Decimal(order_data.shipping_method.unit_price_netto).quantize(Decimal(".01"))

        shipping_tax_amount = order_data.shipping_method.total_price - shipping_amount_without_tax

        customs_threshold_scenario = getattr(order_data.cart, "customs_threshold_scenario", None)

        payment_fee = 0
        payment_tax_amount = 0
        payment_fee_without_tax = 0
        if getattr(order_data, "fee_price", None):
            payment_fee = order_data.fee_price
            payment_tax_amount = Decimal(
                payment_fee - payment_fee / Decimal(1 + order_data.shipping_method.tax_rate)
            ).quantize(Decimal(".01"))
            payment_fee_without_tax = Decimal(payment_fee - payment_tax_amount).quantize(Decimal(".01"))

        # dodajemy fee płatności do shipipingu bo magento nie przyjmuje fee od płatności
        shipping_total = ShippingTotal(
            shipping_amount=Decimal(shipping_amount_without_tax + payment_fee_without_tax).quantize(Decimal(".01")),
            shipping_incl_tax=Decimal(order_data.shipping_method.total_price + payment_fee).quantize(Decimal(".01")),
            shipping_tax_amount=Decimal(shipping_tax_amount + payment_tax_amount).quantize(Decimal(".01")),
        )

        status_histories = StatusHistories(
            comment=order_data.comment, entity_name="order", is_customer_notified=0, is_visible_on_front=1
        )

        report["is_shipping_collected"] = True

        if order_data.payment_method.code in settings.MAPPING_PAYMENT_METHODS.keys():
            magento_name = settings.MAPPING_PAYMENT_METHODS[order_data.payment_method.code]
        else:
            magento_name = settings.MAPPING_PAYMENT_METHODS["default_payment_magento_name"]

        payment_additional_information = {}
        if payment_intent := checkout_order.payment_items.all().first():
            payment_additional_information = {
                "additional_information": {"transaction_id": payment_intent.external_order_id}
            }

        payment = Payment(
            method=magento_name,
            amount_ordered=Payment.calc_amount_ordered(items, shipping_total),
            **payment_additional_information,
        )
        report["is_payment_collected"] = True
        subtotal, tax_amount, subtotal_incl_tax, discount_amount = Order.calc_totals(items, shipping_total)
        discounts = order_data.cart.discounts
        discount_code = map_discount_codes(discounts)
        report["is_discount_collected"] = True

        if discounts:
            # dicount kwotowy
            if Decimal(discounts[0].price_discount) != discount_amount and discounts[0].price_discount > 0:
                discounts_diff = Decimal(discounts[0].price_discount) - discount_amount
                item_with_max_price = max(items, key=lambda item: item.price)
                item_with_max_price.discount_amount += discounts_diff
                discount_amount += discounts_diff

            # dicount procentowy
            if payment.amount_ordered - discount_amount != order_data.total and discounts[0].percent_discount > 0:
                discounts_diff = Decimal(payment.amount_ordered - discount_amount) - order_data.total
                if discounts_diff < Decimal(0.15):
                    item_with_max_price = max(items, key=lambda item: item.price)
                    item_with_max_price.discount_amount += discounts_diff
                    discount_amount += discounts_diff

        if Decimal(payment.amount_ordered - discount_amount) != Decimal(order_data.total):
            logger.info(
                f"There is a difference in amounts between grand_totals and totals {Decimal(payment.amount_ordered - discount_amount)} =/= {Decimal(order_data.total)}"
            )
            raise Exception("There is a difference in amounts between grand_totals and totals")
        channel = Channel.objects.get(idx=channel_idx)

        magento_store_id = (
            channel.lang_channel_to_magento_store.get(order_data.language_code, channel.default_magento_store_id)
            if channel.lang_channel_to_magento_store
            else channel.default_magento_store_id
        )

        order = Order(
            store_id=magento_store_id,
            state=OrderState.PENDING,
            status=OrderStatus.PENDING,
            order_currency_code=order_data.currency_code.upper(),
            items=items,
            billing_address=billing_address,
            extension_attributes=ext_attr,
            status_histories=[status_histories],
            payment=payment,
            increment_id=checkout_order.pretty_id,
            subtotal=subtotal,
            tax_amount=order_data.total_tax,
            subtotal_incl_tax=subtotal_incl_tax,
            total_due=payment.amount_ordered,
            grand_total=payment.amount_ordered - discount_amount,
            discount_amount=-1 * discount_amount,
            discount_tax_compensation_amount=tax_amount - order_data.total_tax,
            coupon_code=discount_code,
            discount_description=discount_code,
            # TODO after adding accounts to checkout change to customer
            customer_email=billing_address.email,
            customer_firstname=billing_address.firstname,
            customer_lastname=billing_address.lastname,
            customer_group_id=0,
            customer_is_guest=1,
            shipping_description=order_data.shipping_method.name,
            shipping_amount=shipping_total.shipping_amount,
            shipping_incl_tax=shipping_total.shipping_incl_tax,
            shipping_tax_amount=shipping_total.shipping_tax_amount,
        )
        entity = order.asdict()

        extension_attributes = entity["entity"]["extension_attributes"]
        if "requested_invoice" in settings.SEND_FIELD_EXTENSION_ATTRIBUTES:
            extension_attributes["requested_invoice"] = (
                order_data.addresses.billing_address.requested_invoice
                if hasattr(order_data.addresses.billing_address, "requested_invoice")
                else False
            )
        if (
            "is_over_vat_threshold" in settings.SEND_FIELD_EXTENSION_ATTRIBUTES
            and customs_threshold_scenario is not None
        ):
            extension_attributes["is_over_vat_threshold"] = customs_threshold_scenario == ABOVE_THRESHOLD

        order_entity = OrderInMagento(
            checkout_order=checkout_order,
            magento_url=MAGENTO_URL,
            success=False,
            request=json.loads(json.dumps(entity, cls=DecimalEncoder)),
        )
        order_entity.save()
        report["is_order_entity_saved"] = True

        client: Client = Client(base_url=MAGENTO_URL, access_token=MAGENTO_TOKEN)
        order_service: OrderService = OrderService(client=client)
        response_data = order_service.create_order(entity)
        report["is_request_done"] = True
        report["magento_response"] = response_data

        order_entity.response = response_data
        order_entity.save()

        if "message" in response_data:
            # mamy error
            report["is_request_done_with_success"] = False
            if response_data["message"] == "Unique constraint violation found":
                raise Exception(
                    "Can not export order to Magento, order already exists in Magento, "
                    f"maybe reset Magento if its on test environment (if not, współczuję), response: {response_data}"
                )
            raise Exception(f"Can not export order to Magento, Magento response: {response_data}")
        else:
            report["is_request_done_with_success"] = True
            to_delete = StockReservation.objects.filter(order=checkout_order).all()
            remove_quantities_for_reservation_object(to_delete)
            order_entity.success = True
            order_entity.entity_id = response_data["entity_id"] if "entity_id" in response_data else None
            order_entity.increment_id = response_data["increment_id"] if "increment_id" in response_data else None
            order_entity.save()
        logger_process.info(
            "Order has been exported.", extra={"details": {"order_id": order_id, "order_pretty_id": order_pretty_id}}
        )
        logger.info(f"Order has been exported: order_id={order_id} order_pretty_id={order_pretty_id}")
        bev.set_details(report)
        bev.finish_with_success(finish_tag="Order has been exported")
    except CheckoutOrder.DoesNotExist:
        msg = f"Can not find order, can not proceed with Export: order_pk={order_pk} order_id={order_id} order_pretty_id={order_pretty_id}"
        logger.error(msg)
        logger_process.error(
            "Can not find order, can not proceed with Export.",
            extra={"details": {"order_pk": order_pk, "order_id": order_id, "order_pretty_id": order_pretty_id}},
        )
        bev.set_details(report)
        bev.finish_with_error(finish_tag="Can not find order in db")
        raise Exception(msg)
    except Exception as e:
        logger.exception(e)
        logger_process.exception(e, extra={"details": {"order_id": order_id, "order_pretty_id": order_pretty_id}})
        bev.set_details(report)
        bev.finish_with_exception(e)
        raise e
