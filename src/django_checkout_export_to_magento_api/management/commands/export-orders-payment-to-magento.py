# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import timedelta

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_checkout.enums import PaymentIntentStatus
from django_checkout.models import Order

from django_checkout_export_to_magento_api.models import InvoiceInMagento
from django_checkout_export_to_magento_api.tasks import export_order_payment_to_magento

DAYS = 1


class Command(BaseCommand):
    help = (
        "Export Checkout Orders Payment to Magento2 as Invoice. Conditions: "
        " | Default days to find orders: " + str(DAYS) + ""
        " | Only orders with payment status COMPLETE"
        " | Only orders with success entry in OrderInMagento table"
        " | Only orders without success entry in InvoiceInMagento table"
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

        invoice_in_magento = InvoiceInMagento.objects.filter(success=True).values("checkout_payment")
        orders: list[Order] = Order.objects.filter(
            channel__idx=channel_idx,
            created__gte=timezone.now() - timedelta(days=days),
            payment_items__payment_status=PaymentIntentStatus.COMPLETE,
            order_in_magento__success=True,
        ).exclude(payment_items__in=invoice_in_magento)
        errors = 0
        for order in orders:
            try:
                self.stdout.write("Processing Order Payment: " + order.pretty_id)
                export_order_payment_to_magento(order_pk=order.pk)
            except Exception:
                errors += 1
                print(f"Exception while processing order {order.pretty_id}")
        if len(orders) == 0:
            print("No orders to process found")
        if errors > 0:
            print(f"Exceptions while processing orders: {errors}")
