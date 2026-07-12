# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.core.exceptions import ObjectDoesNotExist
from django_checkout.models import Order as CheckoutOrder
from django_checkout.models import ShippingIntent as CheckoutShipment
from magento2_sdk.client import Client
from magento2_sdk.services import OrderService

from django_checkout_export_to_magento_api import settings
from django_checkout_export_to_magento_api.models import OrderInMagento, ShipmentInMagento
from django_checkout_export_to_magento_api.repository import order_find_by

from ..bi import ExportOrderShipmentToMagentoEvent

MAGENTO_URL = settings.MAGENTO2_URL_FOR_CHECKOUT_EXPORT
MAGENTO_TOKEN = settings.MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT

logger = logging.getLogger(__name__)
logger_process = logging.getLogger("process")


def export_order_shipment_to_magento(
    order_pk: int | None = None, order_id: str | None = None, order_pretty_id: str | None = None
):
    bev = ExportOrderShipmentToMagentoEvent(
        order_pk=order_pk, order_id=order_id, order_pretty_id=order_pretty_id, is_ongoing_event=True
    )
    report = {
        "is_order_found": False,
        "is_order_in_magento_found": False,
        "is_order_in_magento_success": False,
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

        checkout_shipment: CheckoutShipment = CheckoutShipment.objects.get(order=checkout_order)

        order_in_magento: OrderInMagento = OrderInMagento.objects.filter(
            checkout_order=checkout_order, success=True
        ).latest("pk")
        if order_in_magento is None:
            logger.warning(
                f"There is no OrderInMagento object associated with this order. order_id={order_id} order_pretty_id={order_pretty_id}"
            )
            bev.set_details(report)
            bev.finish_with_error(finish_tag="Sending order to Magento failed")
            return
        report["is_order_in_magento_found"] = True
        if order_in_magento.success is False:
            logger.warning(
                f"Latest process of sending order to Magento ended without SUCCESS. Can not proceed with Shipment. order_id={order_id} order_pretty_id={order_pretty_id} order_in_magento_pk={order_in_magento.pk}"
            )
            logger_process.warning(
                "Latest process of sending order to Magento ended without SUCCESS. Can not proceed with Shipment. Check OrderInMagento entry for details.",
                extra={
                    "details": {
                        "order_id": order_id,
                        "order_pretty_id": order_pretty_id,
                        "order_in_magento_pk": order_in_magento.pk,
                    }
                },
            )
            bev.set_details(report)
            bev.finish_with_error(finish_tag="Sending order to Magento failed")
            return
        report["is_order_in_magento_success"] = True

        client: Client = Client(base_url=MAGENTO_URL, access_token=MAGENTO_TOKEN)
        order_service: OrderService = OrderService(client=client)

        order_magento_data = order_in_magento.response
        items = []
        if "items" in order_magento_data:
            for item in order_magento_data["items"]:
                items.append({"order_item_id": item["item_id"], "qty": item["qty_ordered"]})
        payload = {
            "entity_id": order_in_magento.entity_id,
            "items": items,
            "tracks": [
                {
                    "track_number": checkout_shipment.tracking_link,
                    "title": checkout_shipment.tracking_number,
                    "carrier_code": checkout_shipment.method.code,
                }
            ],
        }
        shipment_in_magento = ShipmentInMagento(
            checkout_shipping=checkout_shipment, magento_url=MAGENTO_URL, success=False, request=payload
        )
        shipment_in_magento.save()
        payload.pop("entity_id")
        response_data = order_service.create_shipment(order_in_magento.entity_id, payload)
        report["is_request_done"] = True
        report["magento_response"] = response_data

        shipment_in_magento.response = response_data
        shipment_in_magento.save()

        if "message" in response_data:
            # mamy error
            report["is_request_done_with_success"] = False
            logger_process.error(
                "Error creating Shipment in Magento",
                extra={
                    "details": {
                        "order_id": order_id,
                        "order_pretty_id": order_pretty_id,
                        "magento_order_entity_id": order_in_magento.entity_id,
                        "magento_response": str(response_data),
                    }
                },
            )
            logger.error(
                f"Error creating Shipment in Magento. order_pretty_id={order_pretty_id} magento_order_entity_id={order_in_magento.entity_id} response={str(response_data)}"
            )
            raise Exception(f"Error creating Shipment in Magento, Magento response: {response_data}")
        else:
            report["is_request_done_with_success"] = True
            shipment_in_magento.success = True
            shipment_in_magento.shipment_id = str(response_data)
            shipment_in_magento.save()
            logger_process.info(
                "Shipment created in Magento",
                extra={
                    "details": {
                        "order_id": order_id,
                        "order_pretty_id": order_pretty_id,
                        "magento_order_entity_id": order_in_magento.entity_id,
                        "magento_shipment_id": str(response_data),
                    }
                },
            )
            logger.info(
                f"Shipment created in Magento. order_pretty_id={order_pretty_id} magento_order_entity_id={order_in_magento.entity_id} magento_shipment_id={str(response_data)}"
            )
        bev.set_details(report)
        bev.finish_with_success(finish_tag="Shipment has been exported")
    except ObjectDoesNotExist:
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
