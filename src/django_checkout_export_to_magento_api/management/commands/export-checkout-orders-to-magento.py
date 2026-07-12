# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from datetime import timedelta

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_checkout.models import Order

from django_checkout_export_to_magento_api.settings import MAGENTO2_EXPORT_GROUND_DATETIME
from django_checkout_export_to_magento_api.tasks import export_checkout_order_to_magento

DAYS = 1
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Export Checkout Orders to Magento2. Conditions: "
        " | Default days to find orders: " + str(DAYS) + ""
        " | Only orders without success entry in OrderInMagento table"
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

        if isinstance(MAGENTO2_EXPORT_GROUND_DATETIME, str):
            try:
                ground_date = timezone.datetime.strptime(MAGENTO2_EXPORT_GROUND_DATETIME, "%Y-%m-%d %H:%M:%S")
                if timezone.is_naive(ground_date):
                    ground_date = timezone.make_aware(ground_date)
            except Exception as e:
                print(f"Exception while parsing ground date: {e}")
                ground_date = None
        else:
            ground_date = None

        query = {"created__gte": ground_date} if ground_date is not None else {}

        orders: list[Order] = (
            Order.objects.filter(channel__idx=channel_idx, created__gte=timezone.now() - timedelta(days=days))
            .filter(**query)
            .exclude(order_in_magento__success=True)
        )
        errors = 0
        for order in orders:
            try:
                self.stdout.write("Processing Order: " + order.pretty_id)
                export_checkout_order_to_magento(channel_idx=channel_idx, order_pk=order.pk)
            except Exception:
                errors += 1
                print(f"Exception while processing order {order.pretty_id}")
        if len(orders) == 0:
            print("No orders to process found")
        if errors > 0:
            print(f"Exceptions while processing orders: {errors}")
