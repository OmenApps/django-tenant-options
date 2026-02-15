"""Namespaced settings for the django-tenant-options app.

Here is what it should look like in the settings.py file of the project:

.. code-block:: python

    DJANGO_TENANT_OPTIONS = {
        "TENANT_MODEL": "example.Tenant",
        # ...
    }

"""

import importlib
import logging
from typing import cast

from django.core.exceptions import ImproperlyConfigured

from django_tenant_options.form_fields import OptionsModelMultipleChoiceField  # noqa: F401


try:
    import_error = None
    from django.conf import settings
    from django.db import models
except ImproperlyConfigured as e:
    import_error = "Settings could not be imported: %s", e
    settings = None  # pylint: disable=C0103
    models = None  # type: ignore[assignment]
except ImportError as e:
    import_error = "Django could not be imported. Settings cannot be loaded: %s", e
    settings = None  # pylint: disable=C0103
    models = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

if import_error:
    logger.error(import_error)


def import_string(dotted_path):
    """Import a dotted module path and return the attribute/class designated by the last name."""
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        logger.exception("Failed to parse dotted_path '%s': %s", dotted_path, err)
        raise ImportError(f"{dotted_path} doesn't look like a module path") from err

    try:
        module = importlib.import_module(module_path)
        logger.debug("Successfully imported module '%s' for dotted_path '%s'", module_path, dotted_path)
    except ImportError as err:
        logger.exception("Failed to import module '%s': %s", module_path, err)
        raise ImportError(f"Module {module_path} does not exist") from err

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        logger.exception("Module '%s' does not define '%s': %s", module_path, class_name, err)
        raise ImportError(f"Module {module_path} does not define {class_name}") from err


class ModelClassConfig:
    """Configuration class for model base classes."""

    def __init__(self):
        """Initialize with lazy-loaded default class references."""
        self._model_class = None
        self._manager_class = None
        self._queryset_class = None
        self._foreignkey_class = None
        self._onetoonefield_class = None
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure the configuration is initialized."""
        if not self._initialized:
            self._model_class = models.Model
            self._manager_class = models.Manager
            self._queryset_class = models.QuerySet
            self._foreignkey_class = models.ForeignKey
            self._onetoonefield_class = models.OneToOneField
            self._initialized = True

    def _import_string(self, dotted_path):
        """Import a dotted module path and return the attribute/class designated by the last name."""
        try:
            module_path, class_name = dotted_path.rsplit(".", 1)
        except ValueError as err:
            raise ImportError(f"{dotted_path} doesn't look like a module path") from err

        try:
            module = importlib.import_module(module_path)
        except ImportError as err:
            raise ImportError(f"Module {module_path} does not exist") from err

        try:
            return getattr(module, class_name)
        except AttributeError as err:
            raise ImportError(f"Module {module_path} does not define {class_name}") from err

    def _resolve_class(self, value):
        """Resolve a class from either a string path or direct class reference."""
        if isinstance(value, str):
            return self._import_string(value)
        return value

    @property
    def model_class(self) -> type:
        """The base class to use for all django-tenant-options models."""
        self._ensure_initialized()
        return cast(type, self._model_class)

    @model_class.setter
    def model_class(self, value):
        """Set the base class to use for all django-tenant-options models."""
        self._model_class = self._resolve_class(value)
        self._initialized = True

    @property
    def manager_class(self) -> type:
        """The base class to use for all django-tenant-options model managers."""
        self._ensure_initialized()
        return cast(type, self._manager_class)

    @manager_class.setter
    def manager_class(self, value):
        """Set the base class to use for all django-tenant-options model managers."""
        self._manager_class = self._resolve_class(value)
        self._initialized = True

    @property
    def queryset_class(self) -> type:
        """The base class to use for all django-tenant-options model querysets."""
        self._ensure_initialized()
        return cast(type, self._queryset_class)

    @queryset_class.setter
    def queryset_class(self, value):
        """Set the base class to use for all django-tenant-options model querysets."""
        self._queryset_class = self._resolve_class(value)
        self._initialized = True

    @property
    def foreignkey_class(self) -> type:
        """The base class to use for all django-tenant-options foreign keys."""
        self._ensure_initialized()
        return cast(type, self._foreignkey_class)

    @foreignkey_class.setter
    def foreignkey_class(self, value):
        """Set the base class to use for all django-tenant-options foreign keys."""
        self._foreignkey_class = self._resolve_class(value)
        self._initialized = True

    @property
    def onetoonefield_class(self) -> type:
        """The base class to use for all django-tenant-options one-to-one fields."""
        self._ensure_initialized()
        return cast(type, self._onetoonefield_class)

    @onetoonefield_class.setter
    def onetoonefield_class(self, value):
        """Set the base class to use for all django-tenant-options one-to-one fields."""
        self._onetoonefield_class = self._resolve_class(value)
        self._initialized = True


# Global config instance for django-tenant-options models
model_config = ModelClassConfig()

_DJANGO_TENANT_OPTIONS = getattr(settings, "DJANGO_TENANT_OPTIONS", {})
"""dict: The settings for the django-tenant-options app."""

# Base class settings
MODEL_CLASS = _DJANGO_TENANT_OPTIONS.get("MODEL_CLASS", models.Model)
"""The base Model class to use. Defaults to django.db.models.Model."""

MANAGER_CLASS = _DJANGO_TENANT_OPTIONS.get("MANAGER_CLASS", models.Manager)
"""The base Manager class to use. Defaults to django.db.models.Manager."""

QUERYSET_CLASS = _DJANGO_TENANT_OPTIONS.get("QUERYSET_CLASS", models.QuerySet)
"""The base QuerySet class to use. Defaults to django.db.models.QuerySet."""

FOREIGNKEY_CLASS = _DJANGO_TENANT_OPTIONS.get("FOREIGNKEY_CLASS", models.ForeignKey)
"""The ForeignKey field class to use. Defaults to django.db.models.ForeignKey."""

ONETOONEFIELD_CLASS = _DJANGO_TENANT_OPTIONS.get("ONETOONEFIELD_CLASS", models.OneToOneField)
"""The OneToOneField field class to use. Defaults to django.db.models.OneToOneField."""

# Convert string references to actual classes
if isinstance(MODEL_CLASS, str):
    MODEL_CLASS = import_string(MODEL_CLASS)
if isinstance(MANAGER_CLASS, str):
    MANAGER_CLASS = import_string(MANAGER_CLASS)
if isinstance(QUERYSET_CLASS, str):
    QUERYSET_CLASS = import_string(QUERYSET_CLASS)
if isinstance(FOREIGNKEY_CLASS, str):
    FOREIGNKEY_CLASS = import_string(FOREIGNKEY_CLASS)
if isinstance(ONETOONEFIELD_CLASS, str):
    ONETOONEFIELD_CLASS = import_string(ONETOONEFIELD_CLASS)

model_config.model_class = MODEL_CLASS
model_config.manager_class = MANAGER_CLASS
model_config.queryset_class = QUERYSET_CLASS
model_config.foreignkey_class = FOREIGNKEY_CLASS
model_config.onetoonefield_class = ONETOONEFIELD_CLASS

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
