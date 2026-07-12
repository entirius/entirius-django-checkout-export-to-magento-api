# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import timedelta

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_checkout.models import Order

from django_checkout_export_to_magento_api.models import ShipmentInMagento
from django_checkout_export_to_magento_api.tasks import export_order_shipment_to_magento

DAYS = 1


class Command(BaseCommand):
    help = (
        "Export Checkout Orders Shipment to Magento2 as. Conditions: "
        " | Default days to find orders: " + str(DAYS) + ""
        " | Only orders with existing shipment"
        " | Only orders with success entry in OrderInMagento table"
        " | Only orders without success entry in ShipmentInMagento table"
    )

    def add_arguments(self, parser):
        parser.add_argument("channel_idx", type=str)
        parser.add_argument("--days", type=int)

    @bi_django_command_decorator
    def handle(self, *args, **options):
        channel_idx = options["channel_idx"]
        days = DAYS
        if options["days"] is not None:
            days = options["days"]

        shipment_in_magento = ShipmentInMagento.objects.filter(success=True).values("checkout_shipping")
        orders: list[Order] = Order.objects.filter(
            channel__idx=channel_idx,
            created__gte=timezone.now() - timedelta(days=days),
            shipping_items__isnull=False,
            order_in_magento__success=True,
        ).exclude(shipping_items__in=shipment_in_magento)
        errors = 0
        for order in orders:
            try:
                self.stdout.write("Processing Order Shipment: " + order.pretty_id)
                export_order_shipment_to_magento(order_pk=order.pk)
            except Exception:
                errors += 1
                print(f"Exception while processing order {order.pretty_id}")
        if len(orders) == 0:
            print("No orders to process found")
        if errors > 0:
            print(f"Exceptions while processing orders: {errors}")
