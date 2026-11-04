# Changelog

## Unreleased

### Added

- `MAPPING_PAYMENT_METHODS["voucher_payment_magento_name"]` (default `free`): the Magento payment of an order the
  vouchers cover.

### Fixed

- An order paid with a voucher, in part or in full, exports to Magento. Checkout takes the voucher off the order
  total and the export's amount check failed on every such order. The voucher goes as an order discount spread over
  the lines, described as `Voucher` with its masked code.
- A line's `base_discount_amount` follows the cent a discount code's rounding moves onto it.

### Changed

- Requires entirius-django-checkout >= 9.3.0: from that release a voucher leaves the lines at their sold price.
  Before it, checkout lowered the lines and counted the voucher in their discount too, which no export can add up.

## 2.0.1 — 2026-11-04

### Fixed

- The export reads the payment method that settles the rest of an order (the first entry that is not a voucher).
  Since entirius-django-checkout 9.0.0 an order's `payment_method` is a list, and the export failed on every order
  with an `AttributeError`.
- An order paid with two methods gets one invoice: the export no longer sends it twice.

Known limit: an order paid with a voucher still fails the export's amount check; how a voucher appears in Magento is
not decided yet.
