# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand

from django_checkout_export_to_magento_api.tasks import export_order_shipment_to_magento


class Command(BaseCommand):
    help = "Export Checkout Order Shipment to Magento2"

    def add_arguments(self, parser):
        parser.add_argument("order_id", type=str, help="use order_pretty_id (10 chars) or order_id (36 chars)")

    @bi_django_command_decorator
    def handle(self, *args, **options):
        order_id_raw = options["order_id"]
        order_id = None
        order_pretty_id = None

        if len(order_id_raw) == 10:
            order_pretty_id = order_id_raw
        elif len(order_id_raw) == 36:
            order_id = order_id_raw
        else:
            raise ValueError("Order id is invalid, use order_pretty_id (10-11 chars) or order_id (36 chars)")
        export_order_shipment_to_magento(order_id=order_id, order_pretty_id=order_pretty_id)
