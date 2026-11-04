# Process logging

Commands can save logs into process.log. Add the following to the host service `settings.py`
(assuming a `process` handler with a JSON formatter is already configured):

```python
LOGGING["loggers"]["django_checkout_export_to_magento_api"] = {
    "handlers": ["process"],
    "level": "DEBUG",
    "propagate": False,
}
```
