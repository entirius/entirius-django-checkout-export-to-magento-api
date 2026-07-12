# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from typing import TYPE_CHECKING

from django.db import models
from idx_normalizator import normalize_idx, validate_idx

if TYPE_CHECKING:
    from django_checkout.models.order import Order as CheckoutOrder
    from django_checkout.models.payment_intent import PaymentIntent as CheckoutPayment
    from django_checkout.models.shipping_intent import ShippingIntent as CheckoutShipping


class OrderInMagento(models.Model):
    checkout_order: "CheckoutOrder" = models.ForeignKey(
        "django_checkout.Order", related_name="order_in_magento", null=True, on_delete=models.SET_NULL
    )
    magento_url = models.CharField(max_length=255)
    success = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)
    request = models.JSONField()
    response = models.JSONField(null=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True)
    increment_id = models.CharField(max_length=100, null=True, blank=True)
    objects = models.Manager()

    class Meta:
        verbose_name = "Order in Magento"
        verbose_name_plural = "Orders in Magento"


class InvoiceInMagento(models.Model):
    checkout_payment: "CheckoutPayment" = models.ForeignKey(
        "django_checkout.PaymentIntent", related_name="invoice_in_magento", null=True, on_delete=models.SET_NULL
    )
    magento_url = models.CharField(max_length=255)
    success = models.BooleanField(default=False)
    request = models.JSONField()
    response = models.JSONField(null=True)
    invoice_id = models.CharField(max_length=100, null=True, blank=True)
    objects = models.Manager()

    class Meta:
        verbose_name = "Invoice in Magento"
        verbose_name_plural = "Invoices in Magento"


class ShipmentInMagento(models.Model):
    checkout_shipping: "CheckoutShipping" = models.ForeignKey(
        "django_checkout.ShippingIntent", related_name="shipping_in_magento", null=True, on_delete=models.SET_NULL
    )
    magento_url = models.CharField(max_length=255)
    success = models.BooleanField(default=False)
    request = models.JSONField()
    response = models.JSONField(null=True)
    shipment_id = models.CharField(max_length=100, null=True, blank=True)
    objects = models.Manager()

    class Meta:
        verbose_name = "Shipping in Magento"
        verbose_name_plural = "Shippings in Magento"


class Channel(models.Model):
    idx = models.CharField(max_length=128, blank=False, null=False, unique=True)
    label = models.CharField(max_length=128, blank=False, null=False, default="", unique=True)
    default_magento_store_id = models.CharField(max_length=128, blank=False, null=False, unique=True)
    lang_channel_to_magento_store = models.JSONField(null=True)
    magento_should_send_email_invoice_confirmation = models.BooleanField(default=False)
    objects = models.Manager()

    @staticmethod
    def normalize_idx(idx):
        """Deprecated"""
        return normalize_idx(idx)

    @staticmethod
    def validate_idx(idx):
        """Deprecated"""
        validate_idx(idx)
