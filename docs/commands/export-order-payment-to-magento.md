# Command

For setup process loging for these commands check project README.md

## Export order payment to magento as Invoice

```bash
manage.py export-order-payment-to-magento --order_primary_key=1 --order_id="123awd2a2312d1" --order_pretty_id="10000004"
```

Paramteters (only one at a time of them is required):

| Name              | Type | Optional | Default |
|-------------------|------|----------|---------|
| order_primary_key | int  | +        | -       |
| order_id          | str  | +        | -       |
| order_pretty_id   | str  | +        | -       |

Conditions:
- Only orders with payment status COMPLETE
- Only orders with succes entry in OrderInMagento table

## Export orders payment to magento as Invoice

```bash
manage.py export-orders-payment-to-magento --days=1
```

Paramteters:

| Name | Type | Optional | Default |
|------|------|----------|---------|
| days | int  | +        | 1       |

Conditions:
- Only orders with created date in range of last days of parameter
- Only orders with payment status COMPLETE
- Only orders with succes entry in OrderInMagento table
- Only orders without succes entry in InvoiceInMagento table


