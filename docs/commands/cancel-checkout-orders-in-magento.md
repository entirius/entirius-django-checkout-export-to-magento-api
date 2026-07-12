# Command

## Cancel orders in magento

```bash
manage.py cancel-checkout-orders-in-magento channel_idx="test_pl" --days=1
```

Paramteters:
channel_idx is required due to more than one store

| Name        | Type | Optional | Default |
|-------------|------|----------|---------|
| channel_idx | str  | -        | -       |
| days        | int  | +        | 1       |

Conditions:
- Only orders with created date in range of last days of parameter
- Only orders without cancel entry in OrderInMagento table and with cancel status in Order table