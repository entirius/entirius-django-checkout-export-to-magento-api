# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import dj_database_url

SECRET_KEY = "test-secret-key-for-checkout-export"

# Settings required at django.setup() time by apps in INSTALLED_APPS
# (django_accounts and django_checkout raise if these are unset).
JWT_SECRET = "test-jwt-secret-for-checkout-export"
PRIVATE_DIR = "/tmp/checkout-export-test-private"
EXPORT_DIR = "/tmp/checkout-export-test-export"
MIGRATION_0023_MECHANISM = 1

# Required by django_pim at import time.
MEDIA_URL = "/media/"
STATIC_URL = "/static/"
TMP_DIR = "/tmp/checkout-export-test-tmp"

# Required by bievents-based BI events at import time.
BI_ENVIRONMENT = "test"
BI_BUSINESS_UNIT = "test"

# Required at import time by tasks/* (read straight off django.conf.settings).
MAGENTO2_URL_FOR_CHECKOUT_EXPORT = "https://magento.example.invalid/rest/"
MAGENTO2_TOKEN_FOR_CHECKOUT_EXPORT = "test-token"  # noqa: S105

# Postgres required (cross-app FK to the checkout/pim/accounts/regional squashes).
# CI provides DATABASE_URL, locally point it at any postgres 15+.
DATABASES = {
    "default": dj_database_url.config(default="postgresql://postgres:postgres@localhost:5432/test"),
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_regional",
    "django_accounts",
    "django_pim",
    "django_pricemanager",
    "django_checkout",
    "django_checkout_export_to_magento_api",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
