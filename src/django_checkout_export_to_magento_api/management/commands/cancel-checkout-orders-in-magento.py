# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from datetime import timedelta

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_checkout.enums import OrderStatus as OrderStatusCheckout
from django_checkout.models import Order

from django_checkout_export_to_magento_api.tasks import cancel_checkout_order_in_magento

DAYS = 1
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Cancel Checkout Orders in Magento2. Conditions: "
        " | Default days to find orders: " + str(DAYS) + ""
        " | Only orders without cancel in OrderInMagento table and with status == CANCELED"
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
        orders: list[Order] = Order.objects.filter(
            channel__idx=channel_idx,
            created__gte=timezone.now() - timedelta(days=days),
            order_in_magento__canceled=False,
            order_in_magento__success=True,
            order_status=OrderStatusCheckout.CANCELED,
        ).distinct()
        errors = 0
        for order in orders:
            try:
                self.stdout.write("Canceling Order: " + order.pretty_id)
                cancel_checkout_order_in_magento(order_pk=order.pk)
            except Exception:
                errors += 1
                print(f"Exception while canceling order {order.pretty_id}")
        if len(orders) == 0:
            print("No orders to cancel found")
        if errors > 0:
            print(f"Exceptions while canceling orders: {errors}")
