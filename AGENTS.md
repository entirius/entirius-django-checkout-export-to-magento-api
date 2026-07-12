# AGENTS.md

Export of Volkanos checkout orders, payments and shipments to the Magento 2 API — distribution
`entirius-django-checkout-export-to-magento-api`, Django app `django_checkout_export_to_magento_api`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_checkout_export_to_magento_api` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.

## Architecture

```
src/django_checkout_export_to_magento_api/
├── apps.py                 # AppConfig (is_volkanos=True)
├── settings.py             # host-overridable settings (URL/token, method mappings)
├── models.py               # Channel + OrderInMagento / InvoiceInMagento / ShipmentInMagento
├── repository.py           # order lookups (by pk / order_id / pretty_id)
├── dto.py                  # OrderIdType enum-ish helper
├── bi.py                   # BI events (bievents)
├── admin.py                # ModelAdmin registrations (4 admins)
├── tasks/                  # export/cancel task functions (called by commands, synchronous)
└── management/commands/    # export-checkout-order(s), export-order(s)-payment/shipment, cancel
```

Models mirror what has been pushed to Magento: one row per exported order / invoice / shipment,
FK to `django_checkout` (Order / PaymentIntent / ShippingIntent). `Channel` maps a checkout
channel to a Magento store (`default_magento_store_id`, per-country store map, email flags).

## Dependencies

| Module | Purpose |
|---|---|
| `django_checkout` | Order / PaymentIntent / ShippingIntent (FK + domain DTO / enums) |
| `magento2_sdk` | Magento 2 REST client (orders, invoices, shipments) |
| `bievents` | BI command decorators + events |
| `idx_normalizator` | idx validation on Channel |

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `MAGENTO2_URL_FOR_CHECKOUT_EXPORT` | `None` | Magento REST base URL |
| `MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT` | `None` | Magento API token |
| `MAPPING_PAYMENT_METHODS` | see `settings.py` | checkout provider → Magento payment code |
| `MAPPING_SHIPPING_METHODS` | see `settings.py` | checkout shipping → Magento carrier code |
| `SEND_FIELD_EXTENSION_ATTRIBUTES` | `["requested_invoice", "is_over_vat_threshold"]` | order extension attributes forwarded to Magento |
| `MAGENTO2_EXPORT_GROUND_DATETIME` | `None` | only export orders created after this datetime |

## Testing

```bash
# Postgres required; tests/settings.py reads DATABASE_URL
# (default postgresql://postgres:postgres@localhost:5432/test).
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test make test
```

Test suite is an import smoke test (`tests/test_smoke.py`) — real exporter tests are an open TODO.

## References

- `docs/commands/` — management command reference (parameters, examples).
