# Changelog

## 2.0.1 — 2026-11-04

### Fixed

- The export reads the payment method that settles the rest of an order (the first entry that is not a voucher).
  Since entirius-django-checkout 9.0.0 an order's `payment_method` is a list, and the export failed on every order
  with an `AttributeError`.
- An order paid with two methods gets one invoice: the export no longer sends it twice.

Known limit: an order paid with a voucher still fails the export's amount check; how a voucher appears in Magento is
not decided yet.
