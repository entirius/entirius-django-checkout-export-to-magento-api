# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.conf import settings
from django_checkout.models import Order as CheckoutOrder
from magento2_sdk.client import Client
from magento2_sdk.services import OrderService

from django_checkout_export_to_magento_api.models import OrderInMagento
from django_checkout_export_to_magento_api.repository import order_find_by

from ..bi import ExportOrderToMagentoEvent

MAGENTO_URL = settings.MAGENTO2_URL_FOR_CHECKOUT_EXPORT
MAGENTO_TOKEN = settings.MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT

logger = logging.getLogger(__name__)
logger_process = logging.getLogger("process")


def cancel_checkout_order_in_magento(
    order_pk: int | None = None, order_id: str | None = None, order_pretty_id: str | None = None
):
    """
    exactly one of: order_pk, order_id or order_pretty_id must be set
    """
    bev = ExportOrderToMagentoEvent(
        order_pk=order_pk, order_id=order_id, order_pretty_id=order_pretty_id, is_ongoing_event=True
    )

    report = {
        "is_order_found": False,
        "is_order_in_magento_found": False,
        "is_request_done": False,
        "is_request_done_with_success": False,
        "is_mark_as_canceled": False,
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
        order_in_magento = OrderInMagento.objects.get(checkout_order=checkout_order)

        client: Client = Client(base_url=MAGENTO_URL, access_token=MAGENTO_TOKEN)
        order_service: OrderService = OrderService(client=client)
        response_data = order_service.cancel_order(order_in_magento.entity_id)
        report["is_request_done"] = True
        report["magento_response"] = response_data
        if not response_data:
            raise Exception(f"Can not export order to Magento, Magento response: {response_data}")
        else:
            report["is_request_done_with_success"] = True
            order_in_magento.canceled = True
            order_in_magento.save()
            report["is_mark_as_canceled"] = True
        logger_process.info(
            "Order has been canceled.", extra={"details": {"order_id": order_id, "order_pretty_id": order_pretty_id}}
        )
        logger.info(f"Order has been canceled: order_id={order_id} order_pretty_id={order_pretty_id}")
        bev.set_details(report)
        bev.finish_with_success(finish_tag="Order has been exported")
    except CheckoutOrder.DoesNotExist:
        msg = f"Can not find order, can not proceed with Cancel: order_pk={order_pk} order_id={order_id} order_pretty_id={order_pretty_id}"
        logger.error(msg)
        logger_process.error(
            "Can not find order, can not proceed with cancel.",
            extra={"details": {"order_pk": order_pk, "order_id": order_id, "order_pretty_id": order_pretty_id}},
        )
        bev.set_details(report)
        bev.finish_with_error(finish_tag="Can not find order in db")
        raise Exception(msg)
    except OrderInMagento.DoesNotExist:
        msg = f"Can not find OrderInMagento for order: order_pk={order_pk} order_id={order_id} order_pretty_id={order_pretty_id}. Waiting for send by export-checkout-orders-to-magento"
        logger.error(msg)
        logger_process.error(
            "Can not find OrderInMagento for order, can not proceed with cancel.",
            extra={"details": {"order_pk": order_pk, "order_id": order_id, "order_pretty_id": order_pretty_id}},
        )
        bev.set_details(report)
        bev.finish_with_error(finish_tag="Can not find OrderInMagento for order in db")
        raise Exception(msg)
    except Exception as e:
        msg = f"Exception while canceling order in Magento: order_id={order_id} order_pretty_id={order_pretty_id}, message: {e}"
        logger.error(msg)
        logger_process.error(
            "Exception while canceling order in Magento.",
            extra={"details": {"order_id": order_id, "order_pretty_id": order_pretty_id}},
        )
        bev.set_details(report)
        bev.finish_with_exception(e)
        raise e
