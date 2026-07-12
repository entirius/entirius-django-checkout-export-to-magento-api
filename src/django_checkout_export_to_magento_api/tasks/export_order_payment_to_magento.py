# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.core.exceptions import ObjectDoesNotExist
from django_checkout.enums import PaymentIntentStatus
from django_checkout.models import Order as CheckoutOrder
from django_checkout.models import PaymentIntent as CheckoutPayment
from magento2_sdk.client import Client
from magento2_sdk.services import InvoiceService

from django_checkout_export_to_magento_api import settings
from django_checkout_export_to_magento_api.models import Channel, InvoiceInMagento, OrderInMagento
from django_checkout_export_to_magento_api.repository import order_find_by

from ..bi import ExportOrderPaymentToMagentoEvent

MAGENTO_URL = settings.MAGENTO2_URL_FOR_CHECKOUT_EXPORT
MAGENTO_TOKEN = settings.MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT

logger = logging.getLogger(__name__)
logger_process = logging.getLogger("process")


def export_order_payment_to_magento(
    order_pk: int | None = None, order_id: str | None = None, order_pretty_id: str | None = None
):
    bev = ExportOrderPaymentToMagentoEvent(
        order_pk=order_pk, order_id=order_id, order_pretty_id=order_pretty_id, is_ongoing_event=True
    )
    report = {
        "is_order_found": False,
        "is_payment_complete": False,
        "is_order_in_magento_found": False,
        "is_order_in_magento_success": False,
        "is_request_done": False,
        "is_request_done_with_success": False,
        "payment_status": None,
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
        checkout_payment: CheckoutPayment = CheckoutPayment.objects.get(order=checkout_order)
        report["payment_status"] = checkout_payment.payment_status
        if checkout_payment.payment_status != PaymentIntentStatus.COMPLETE:
            report["is_payment_complete"] = False
            logger.warning(
                f"Order payment status is not COMPLETE. Can not proceed with Invoice. order_pretty_id={checkout_order.pretty_id}"
            )
            logger_process.warning(
                "Order payment status is not COMPLETE. Can not proceed with Invoice.",
                extra={"details": {"order_id": order_id, "order_pretty_id": order_pretty_id}},
            )
            bev.set_details(report)
            bev.finish_with_success(finish_tag="Payment status is not complete")
            return
        report["is_payment_complete"] = True

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
                f"Latest process of sending order to Magento ended without SUCCESS. Can not proceed with Invoice. order_id={order_id} order_pretty_id={order_pretty_id} order_in_magento_pk={order_in_magento.pk}"
            )
            logger_process.warning(
                "Latest process of sending order to Magento ended without SUCCESS. Can not proceed with Invoice. Check OrderInMagento entry for details.",
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
        invoice_service: InvoiceService = InvoiceService(client=client)

        capture = False
        channel = Channel.objects.filter(idx=checkout_order.channel.idx).first()
        notify = False
        if channel:
            notify = channel.magento_should_send_email_invoice_confirmation
        payload = {"entity_id": order_in_magento.entity_id, "capture": capture, "notify": notify}
        invoice_in_magento = InvoiceInMagento(
            checkout_payment=checkout_payment, magento_url=MAGENTO_URL, success=False, request=payload
        )
        invoice_in_magento.save()
        response_data = invoice_service.create_invoice(order_in_magento.entity_id, capture, notify)
        report["is_request_done"] = True
        report["magento_response"] = response_data

        invoice_in_magento.response = response_data
        invoice_in_magento.save()

        if "message" in response_data:
            # mamy error
            report["is_request_done_with_success"] = False
            logger_process.error(
                "Error creating invoice in Magento",
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
                f"Error creating invoice in Magento. order_pretty_id={order_pretty_id} magento_order_entity_id={order_in_magento.entity_id} response={str(response_data)}"
            )
            raise Exception(f"Error creating invoice in Magento, Magento response: {response_data}")
        else:
            report["is_request_done_with_success"] = True
            invoice_in_magento.success = True
            invoice_in_magento.invoice_id = str(response_data)
            invoice_in_magento.save()
            logger_process.info(
                "Invoice created in Magento",
                extra={
                    "details": {
                        "order_id": order_id,
                        "order_pretty_id": order_pretty_id,
                        "magento_order_entity_id": order_in_magento.entity_id,
                        "magento_invoice_id": str(response_data),
                    }
                },
            )
            logger.info(
                f"Invoice created in Magento. order_pretty_id={order_pretty_id} magento_order_entity_id={order_in_magento.entity_id} magento_invoice_id={str(response_data)}"
            )
        bev.set_details(report)
        bev.finish_with_success(finish_tag="Payment has been exported")
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
