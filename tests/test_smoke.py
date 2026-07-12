# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Smoke test: every public submodule imports cleanly under a configured Django."""

import importlib

import pytest

MODULES = [
    "django_checkout_export_to_magento_api.apps",
    "django_checkout_export_to_magento_api.settings",
    "django_checkout_export_to_magento_api.models",
    "django_checkout_export_to_magento_api.admin",
    "django_checkout_export_to_magento_api.bi",
    "django_checkout_export_to_magento_api.dto",
    "django_checkout_export_to_magento_api.repository",
    "django_checkout_export_to_magento_api.tasks",
    "django_checkout_export_to_magento_api.tasks.cancel_checkout_order_in_magento",
    "django_checkout_export_to_magento_api.tasks.export_checkout_order_to_magento",
    "django_checkout_export_to_magento_api.tasks.export_order_payment_to_magento",
    "django_checkout_export_to_magento_api.tasks.export_order_shipment_to_magento",
    "django_checkout_export_to_magento_api.management.commands.cancel-checkout-orders-in-magento",
    "django_checkout_export_to_magento_api.management.commands.export-checkout-order-to-magento",
    "django_checkout_export_to_magento_api.management.commands.export-checkout-orders-to-magento",
    "django_checkout_export_to_magento_api.management.commands.export-order-payment-to-magento",
    "django_checkout_export_to_magento_api.management.commands.export-order-shipment-to-magento",
    "django_checkout_export_to_magento_api.management.commands.export-orders-payment-to-magento",
    "django_checkout_export_to_magento_api.management.commands.export-orders-shipment-to-magento",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)
