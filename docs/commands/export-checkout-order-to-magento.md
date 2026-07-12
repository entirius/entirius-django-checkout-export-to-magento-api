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