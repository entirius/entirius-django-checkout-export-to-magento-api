# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

MAGENTO2_URL_FOR_CHECKOUT_EXPORT = getattr(settings, "MAGENTO2_URL_FOR_CHECKOUT_EXPORT", None)
MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT = getattr(settings, "MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT", None)

MAPPING_PAYMENT_METHODS_DEFAULT = {
    "default_payment_magento_name": "banktransfer",
    "cod": "cashondelivery",
    "paypal": "volkanos_paypal",
}
MAPPING_PAYMENT_METHODS = getattr(settings, "MAPPING_PAYMENT_METHODS", MAPPING_PAYMENT_METHODS_DEFAULT)

if not isinstance(MAPPING_PAYMENT_METHODS, dict):
    raise Exception("MAPPING_PAYMENT_METHODS must be a dict")

if "default_payment_magento_name" not in MAPPING_PAYMENT_METHODS.keys():
    MAPPING_PAYMENT_METHODS["default_payment_magento_name"] = "banktransfer"

MAPPING_SHIPPING_METHODS_DEFAULT = {"default_shipping_magento_code": "flatrate_flatrate"}

MAPPING_SHIPPING_METHODS = getattr(settings, "MAPPING_SHIPPING_METHODS", MAPPING_SHIPPING_METHODS_DEFAULT)
SEND_FIELD_EXTENSION_ATTRIBUTES = getattr(
    settings, "SEND_FIELD_EXTENSION_ATTRIBUTES", ["requested_invoice", "is_over_vat_threshold"]
)

if not isinstance(MAPPING_SHIPPING_METHODS, dict):
    raise Exception("MAPPING_SHIPPING_METHODS must be a dict")

if "default_shipping_magento_code" not in MAPPING_SHIPPING_METHODS.keys():
    MAPPING_SHIPPING_METHODS["default_shipping_magento_code"] = "flatrate_flatrate"


# Set up this date when you want to export orders since given date
# Datetime should be in format %Y-%m-%d %H:%M:%S with timezone used in django settings (default UTC)
MAGENTO2_EXPORT_GROUND_DATETIME = getattr(settings, "MAGENTO2_EXPORT_GROUND_DATETIME", None)
