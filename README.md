# entirius-django-checkout-export-to-magento-api

A Django module that exports orders, payments and shipments from Entirius, the open-source modular ecommerce platform,
to an existing Magento 2 store over REST. Payments arrive in Magento as invoices, and every export is recorded so
that a re-run sends only what is still missing.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-checkout-export-to-magento-api.svg)](https://pypi.org/project/entirius-django-checkout-export-to-magento-api/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-checkout-export-to-magento-api.svg)](https://pypi.org/project/entirius-django-checkout-export-to-magento-api/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-checkout-export-to-magento-api/blob/develop/LICENSE)

## What it does

- Exports checkout orders to Magento 2, one order or every recent order of a channel.
- Exports completed payments as Magento invoices and shipments as Magento shipments.
- Cancels in Magento the orders that were canceled in the checkout.
- Maps payment and shipping methods of the checkout to Magento codes through settings.
- Maps each checkout channel to a Magento store, with a per-language store map.
- Records every exported order, invoice and shipment, so re-runs skip what already succeeded.

## Installation

```shell
uv add entirius-django-checkout-export-to-magento-api
pip install entirius-django-checkout-export-to-magento-api
```

```python
INSTALLED_APPS = [
    ...
    "django_checkout",
    "django_checkout_export_to_magento_api",
]
```

`django_checkout` brings its own app requirements. Required settings: `MAGENTO2_URL_FOR_CHECKOUT_EXPORT` and
`MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT`.
The module also reads `BI_ENVIRONMENT` and `BI_BUSINESS_UNIT` (BI events) at import time, without a default.

Optional settings: `MAPPING_PAYMENT_METHODS`, `MAPPING_SHIPPING_METHODS`, `SEND_FIELD_EXTENSION_ATTRIBUTES`,
`MAGENTO2_EXPORT_GROUND_DATETIME`; reference with defaults in
https://github.com/entirius/entirius-django-checkout-export-to-magento-api/blob/develop/AGENTS.md (section Settings).

## Quick start

```python
# settings.py
MAGENTO2_URL_FOR_CHECKOUT_EXPORT = "https://magento.example.com/rest/"
MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT = "<api-token>"

# a shell or a scheduled job
from django.core.management import call_command

call_command("export-checkout-orders-to-magento", "default", days=7)
```

The positional argument is the `idx` of the checkout channel; `days` is how far back orders are looked up
(default 1).

## Requirements

- Python 3.11 or newer, Django 5.0 or newer.
- PostgreSQL.
- A Magento 2 store with a REST API integration token.
- Entirius packages pulled in: `entirius-django-checkout` (orders, payment and shipping intents), `entirius-py-magento2-sdk`
  (Magento 2 REST client), `entirius-py-bievents` (BI events), `entirius-py-idx-normalizator` (channel idx).

## Documentation

- Module docs (management commands, process logging): https://github.com/entirius/entirius-django-checkout-export-to-magento-api/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Releases: https://github.com/entirius/entirius-django-checkout-export-to-magento-api/releases

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos) and sends its orders to an existing
Magento 2 store.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Checkout module: https://github.com/entirius/entirius-django-checkout
- Magento 2 SDK it uses: https://github.com/entirius/entirius-py-magento2-sdk
- Sibling bridges: https://github.com/entirius/entirius-django-checkout-import-from-magento-api,
  https://github.com/entirius/entirius-django-pim-export-to-magento-api,
  https://github.com/entirius/entirius-django-accounts-export-to-magento-api

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-checkout-export-to-magento-api/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-checkout-export-to-magento-api/blob/develop/LICENSE.
