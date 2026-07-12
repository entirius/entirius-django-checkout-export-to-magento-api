# entirius-django-checkout-export-to-magento-api

Exports `django_checkout` orders, payments (as invoices) and shipments to a Magento 2 instance
via its REST API. Part of the Volkanos e-commerce module family.

## Installation

```shell
pip install entirius-django-checkout-export-to-magento-api
```

## Configuration

```python
MAGENTO2_URL_FOR_CHECKOUT_EXPORT = "https://your-magento-host/rest/"
MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT = "<api-token>"
```

Optional mappings (see `src/django_checkout_export_to_magento_api/settings.py` for defaults):
`MAPPING_PAYMENT_METHODS`, `MAPPING_SHIPPING_METHODS`, `SEND_FIELD_EXTENSION_ATTRIBUTES`,
`MAGENTO2_EXPORT_GROUND_DATETIME`.

## Development

```shell
make install   # uv sync (incl. extras)
make test      # run tests
make check     # ruff lint + format-check
```

## Process Logging

Commands can save logs into process.log. Add the following to the host service `settings.py`
(assuming a `process` handler with a JSON formatter is already configured):

```python
LOGGING["loggers"]["django_checkout_export_to_magento_api"] = {
    "handlers": ["process"],
    "level": "DEBUG",
    "propagate": False,
}
```

## Commands

See `docs/commands/` for the management command reference.

## License

MPL-2.0
