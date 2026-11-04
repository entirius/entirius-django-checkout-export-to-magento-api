# Command

## Export order  to magento

```bash
manage.py export-checkout-order-to-magento channel_idx="test_pl" --order_primary_key=1 --order_id="123awd2a2312d1" --order_pretty_id="10000004"
```

Paramteters (only one at a time of them is required):
channel_idx is required due to more than one store

| Name              | Type | Optional | Default |
|-------------------|------|----------|---------|
| channel_idx       | str  | -        | -       |
| order_primary_key | int  | +        | -       |
| order_id          | str  | +        | -       |
| order_pretty_id   | str  | +        | -       |


## Export orders to magento

```bash
manage.py export-checkout-orders-to-magento channel_idx="test_pl" --days=1
```

Paramteters:
channel_idx is required due to more than one store

| Name        | Type | Optional | Default |
|-------------|------|----------|---------|
| channel_idx | str  | -        | -       |
| days        | int  | +        | 1       |

Conditions:
- Only orders with created date in range of last days of parameter
- Only orders without succes entry in OrderInMagento table

## Vouchers

Checkout takes a voucher off the order total and keeps the lines at their sold price. Magento Open Source has no
gift card or second payment, so the export sends the voucher as an order discount:

- `discount_amount` holds discount codes and vouchers together; each line carries its share of the voucher, pro rata
  to what the line still costs, so Magento's invoice adds up to the order's `grand_total`.
- `discount_description` reads `<codes> Voucher <masked codes>` (`PROMO10 Voucher 26WT********`); `coupon_code`
  stays the discount codes only. A voucher code that checkout did not mask is never sent.
- The payment is the method that settles the rest; an order the vouchers cover goes with
  `MAPPING_PAYMENT_METHODS["voucher_payment_magento_name"]`, default `free` (Zero Subtotal Checkout).
- The voucher counts at most what the lines cost: before checkout 10.1 `voucher_amount_applied` may exceed the cart.
- Needs checkout >= 9.3.0, where the voucher leaves the lines at their sold price.
