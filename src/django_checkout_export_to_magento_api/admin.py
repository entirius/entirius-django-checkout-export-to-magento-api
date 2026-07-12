# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from .models import Channel, InvoiceInMagento, OrderInMagento, ShipmentInMagento


@admin.register(OrderInMagento)
class OrderInMagentoAdmin(admin.ModelAdmin):
    model = OrderInMagento

    list_display = ["checkout_order", "magento_url", "success", "canceled", "entity_id", "increment_id"]
    list_filter = ["success", "magento_url", "canceled"]
    search_fields = ["checkout_order__pk", "checkout_order__order_id", "increment_id"]

    readonly_fields = [
        "canceled",
        "checkout_order",
        "magento_url",
        "success",
        "request",
        "response",
        "entity_id",
        "increment_id",
    ]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InvoiceInMagento)
class InvoiceInMagentoAdmin(admin.ModelAdmin):
    model = InvoiceInMagento

    list_display = ["checkout_payment", "magento_url", "success", "invoice_id"]
    list_filter = ["success", "magento_url"]
    search_fields = ["checkout_payment__pk", "invoice_id"]

    readonly_fields = ["checkout_payment", "magento_url", "success", "request", "response", "invoice_id"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ShipmentInMagento)
class ShipmentInMagentoAdmin(admin.ModelAdmin):
    model = ShipmentInMagento

    list_display = ["checkout_shipping", "magento_url", "success", "shipment_id"]
    list_filter = ["success", "magento_url"]
    search_fields = ["checkout_shipping__pk", "shipment_id"]

    readonly_fields = ["checkout_shipping", "magento_url", "success", "request", "response", "shipment_id"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    model = Channel
    list_display = ["idx", "label", "default_magento_store_id", "magento_should_send_email_invoice_confirmation"]
