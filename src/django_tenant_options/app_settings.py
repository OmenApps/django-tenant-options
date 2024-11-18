"""Namespaced settings for the django-tenant-options app.

Here is what it should look like in the settings.py file of the project:

.. code-block:: python

    DJANGO_TENANT_OPTIONS = {
        "TENANT_MODEL": "example.Tenant",
        # ...
    }

"""

from django.core.exceptions import ImproperlyConfigured


try:
    from django.conf import settings
except ImproperlyConfigured:
    print("**** ImproperlyConfigured")
    settings = None  # pylint: disable=C0103
except ImportError:
    print("**** ImportError")
    settings = None  # pylint: disable=C0103
from django.db import models

from django_tenant_options.form_fields import (  # noqa: F401
    OptionsModelMultipleChoiceField,
)


_DJANGO_TENANT_OPTIONS = getattr(settings, "DJANGO_TENANT_OPTIONS", {})
"""dict: The settings for the django-tenant-options app."""

TENANT_MODEL = _DJANGO_TENANT_OPTIONS.get("TENANT_MODEL", "django_tenant_options.Tenant")
"""str: The model to use for the tenant."""

TENANT_ON_DELETE = _DJANGO_TENANT_OPTIONS.get("TENANT_ON_DELETE", models.CASCADE)
"""What should happen to Options and Selections when a related Tenant is deleted.

This sets the on_delete option for the `tenant` ForeignKey field on these models, and should use one of [django's
standard `on_delete` arguments](https://docs.djangoproject.com/en/dev/ref/models/fields/#arguments)
(e.g. models.CASCADE, models.PROTECT, models.SET_NULL, etc).
"""

OPTION_ON_DELETE = _DJANGO_TENANT_OPTIONS.get("OPTION_ON_DELETE", models.CASCADE)
"""What should happen to Selections when a related Option is deleted.

By default, Options are soft-deleted, so this setting is not used.

This sets the on_delete option for the `option` ForeignKey field on Selection models, and should use one of [django's
standard `on_delete` arguments](https://docs.djangoproject.com/en/dev/ref/models/fields/#arguments)
(e.g. models.CASCADE, models.PROTECT, models.SET_NULL, etc).
"""

TENANT_MODEL_RELATED_NAME = _DJANGO_TENANT_OPTIONS.get("TENANT_MODEL_RELATED_NAME", "%(app_label)s_%(class)s_related")
"""str: The related name template for the tenant model."""

TENANT_MODEL_RELATED_QUERY_NAME = _DJANGO_TENANT_OPTIONS.get(
    "TENANT_MODEL_RELATED_QUERY_NAME", "%(app_label)s_%(class)ss"
)
"""str: The related query name template for the tenant model."""

ASSOCIATED_TENANTS_RELATED_NAME = _DJANGO_TENANT_OPTIONS.get(
    "ASSOCIATED_TENANTS_RELATED_NAME", "%(app_label)s_%(class)s_selections"
)
"""str: The related name template for the associated tenants model.

This is used for the ManyToManyField from an Option model to a Tenant model.
"""

ASSOCIATED_TENANTS_RELATED_QUERY_NAME = _DJANGO_TENANT_OPTIONS.get(
    "ASSOCIATED_TENANTS_RELATED_QUERY_NAME", "%(app_label)s_%(class)ss_selected"
)
"""str: The related query name template for the associated tenants model.

This is used for the ManyToManyField from an Option model to a Tenant model.
"""

OPTION_MODEL_RELATED_NAME = _DJANGO_TENANT_OPTIONS.get("OPTION_MODEL_RELATED_NAME", "%(app_label)s_%(class)s_related")
"""str: The related name template to use for all Option models."""

OPTION_MODEL_RELATED_QUERY_NAME = _DJANGO_TENANT_OPTIONS.get(
    "OPTION_MODEL_RELATED_QUERY_NAME", "%(app_label)s_%(class)ss"
)
"""str: The related query name template to use for all Option models."""

DB_VENDOR_OVERRIDE = _DJANGO_TENANT_OPTIONS.get("DB_VENDOR_OVERRIDE", None)
"""str: The database vendor to use for generating triggers if the default is not one of the supported vendors.

In some cases, you may use a custom database backend, but the underlying database is still one of the supported
vendors. In this case, you can specify that supported database vendor here.

An example of this is if you are using Django's Postgis backend, but the underlying database is still PostgreSQL.

Allowed values are 'postgresql', 'mysql', 'sqlite', 'oracle'.
"""

DEFAULT_MULTIPLE_CHOICE_FIELD = _DJANGO_TENANT_OPTIONS.get(
    "DEFAULT_MULTIPLE_CHOICE_FIELD", OptionsModelMultipleChoiceField
)
"""The default form field to use for multiple choice fields. This can also be overridden per form."""

DISABLE_FIELD_FOR_DELETED_SELECTION = _DJANGO_TENANT_OPTIONS.get("DISABLE_FIELD_FOR_DELETED_SELECTION", False)
"""bool: The behavior to use in user-facing forms when a selection was deleted by the tenant.

By default, if a selection was deleted, the user must select a new option when updating a form. If this setting is
True, the deleted selection will be displayed in the form, but disabled so it cannot be changed.

In both cases, the deleted selection cannot be used in new forms.
"""
