# Configuration Reference

All `django-tenant-options` settings are configured through a single dictionary in your Django `settings.py`:

```python
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "yourapp.Tenant",
    # ... other settings
}
```

Individual models can override most settings by setting the corresponding class attribute directly.

## Required settings

### `TENANT_MODEL`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"django_tenant_options.Tenant"` |
| **Required** | Yes |

The dotted path to your tenant model. This is the only setting you must configure.

```python
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "myapp.Tenant",
}
```

## Tenant relationship settings

### `TENANT_ON_DELETE`

| | |
|---|---|
| **Type** | Django `on_delete` action |
| **Default** | `models.CASCADE` |

What happens to Options and Selections when a related Tenant is deleted. Uses Django's standard [on_delete arguments](https://docs.djangoproject.com/en/stable/ref/models/fields/#arguments).

```python
from django.db import models

DJANGO_TENANT_OPTIONS = {
    "TENANT_ON_DELETE": models.CASCADE,  # or models.PROTECT, models.SET_NULL, etc.
}
```

### `TENANT_MODEL_RELATED_NAME`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"%(app_label)s_%(class)s_related"` |

The `related_name` template for the `tenant` ForeignKey on Option and Selection models. Uses Django's [related_name](https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey.related_name) interpolation.

### `TENANT_MODEL_RELATED_QUERY_NAME`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"%(app_label)s_%(class)ss"` |

The `related_query_name` template for the `tenant` ForeignKey on Option and Selection models.

## Option relationship settings

### `OPTION_ON_DELETE`

| | |
|---|---|
| **Type** | Django `on_delete` action |
| **Default** | `models.CASCADE` |

What happens to Selections when a related Option is deleted. Since Options use soft deletes by default, this setting is rarely triggered.

### `OPTION_MODEL_RELATED_NAME`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"%(app_label)s_%(class)s_related"` |

The `related_name` template for the `option` ForeignKey on Selection models.

### `OPTION_MODEL_RELATED_QUERY_NAME`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"%(app_label)s_%(class)ss"` |

The `related_query_name` template for the `option` ForeignKey on Selection models.

### `ASSOCIATED_TENANTS_RELATED_NAME`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"%(app_label)s_%(class)s_selections"` |

The `related_name` template for the `associated_tenants` ManyToManyField from Option to Tenant (through the Selection model).

### `ASSOCIATED_TENANTS_RELATED_QUERY_NAME`

| | |
|---|---|
| **Type** | `str` |
| **Default** | `"%(app_label)s_%(class)ss_selected"` |

The `related_query_name` template for the `associated_tenants` ManyToManyField.

## Base class settings

These settings let you replace the default Django base classes with custom ones (e.g., from [django-auto-prefetch](https://github.com/tolomea/django-auto-prefetch)). Values can be class references or dotted string paths.

### `MODEL_CLASS`

| | |
|---|---|
| **Type** | class or `str` |
| **Default** | `django.db.models.Model` |

### `MANAGER_CLASS`

| | |
|---|---|
| **Type** | class or `str` |
| **Default** | `django.db.models.Manager` |

### `QUERYSET_CLASS`

| | |
|---|---|
| **Type** | class or `str` |
| **Default** | `django.db.models.QuerySet` |

### `FOREIGNKEY_CLASS`

| | |
|---|---|
| **Type** | class or `str` |
| **Default** | `django.db.models.ForeignKey` |

### `ONETOONEFIELD_CLASS`

| | |
|---|---|
| **Type** | class or `str` |
| **Default** | `django.db.models.OneToOneField` |

**Example:**

```python
import auto_prefetch

DJANGO_TENANT_OPTIONS = {
    "MODEL_CLASS": auto_prefetch.Model,
    "MANAGER_CLASS": "auto_prefetch.Manager",
    "QUERYSET_CLASS": "auto_prefetch.QuerySet",
    "FOREIGNKEY_CLASS": auto_prefetch.ForeignKey,
    "ONETOONEFIELD_CLASS": "auto_prefetch.OneToOneField",
}
```

See [Customization](customization.md) for programmatic configuration via `model_config`.

## Form settings

### `DEFAULT_MULTIPLE_CHOICE_FIELD`

| | |
|---|---|
| **Type** | class or `str` |
| **Default** | `OptionsModelMultipleChoiceField` |

The form field class used by `SelectionsForm` for the selections widget. Override to customize how options are displayed.

```python
DJANGO_TENANT_OPTIONS = {
    "DEFAULT_MULTIPLE_CHOICE_FIELD": "yourapp.forms.CustomOptionsField",
}
```

### `DISABLE_FIELD_FOR_DELETED_SELECTION`

| | |
|---|---|
| **Type** | `bool` |
| **Default** | `False` |

Controls how `UserFacingFormMixin` handles existing records that reference a deleted selection.

- **`False`** (default): The user must select a new option when editing the record.
- **`True`**: The deleted option appears in the form but is disabled (read-only), preserving the historical value.

In both cases, deleted options are never shown in forms for new records.

## Database settings

### `DB_VENDOR_OVERRIDE`

| | |
|---|---|
| **Type** | `str` or `None` |
| **Default** | `None` |

Override automatic database vendor detection for trigger generation. Useful when using a custom database backend (e.g., PostGIS) where the underlying database is a supported vendor.

```python
DJANGO_TENANT_OPTIONS = {
    "DB_VENDOR_OVERRIDE": "postgresql",  # "postgresql", "mysql", "sqlite", or "oracle"
}
```

## Full example

Here's a complete settings configuration:

```python
from django.db import models

DJANGO_TENANT_OPTIONS = {
    # Required
    "TENANT_MODEL": "myapp.Tenant",

    # Tenant relationships
    "TENANT_ON_DELETE": models.CASCADE,
    "TENANT_MODEL_RELATED_NAME": "%(app_label)s_%(class)s_related",
    "TENANT_MODEL_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss",

    # Option relationships
    "OPTION_ON_DELETE": models.CASCADE,
    "OPTION_MODEL_RELATED_NAME": "%(app_label)s_%(class)s_related",
    "OPTION_MODEL_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss",
    "ASSOCIATED_TENANTS_RELATED_NAME": "%(app_label)s_%(class)s_selections",
    "ASSOCIATED_TENANTS_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss_selected",

    # Database
    "DB_VENDOR_OVERRIDE": None,

    # Forms
    "DISABLE_FIELD_FOR_DELETED_SELECTION": False,
}
```

## System checks

`django-tenant-options` registers Django system checks that run automatically during `manage.py check`, `migrate`, and `runserver`. These checks validate your model configuration.

### Option model checks

| Check ID | Level | Description |
|----------|-------|-------------|
| `django_tenant_options.I001` | Info | Option model manager doesn't inherit from `OptionManager`. Filtering may not work as expected. |
| `django_tenant_options.E002` | Error | Option model manager uses a queryset that doesn't inherit from `OptionQuerySet`. |
| `django_tenant_options.E003` | Error | Option model has no manager inheriting from `OptionManager` with `OptionQuerySet`. |
| `django_tenant_options.W007` | Warning | Option model may be missing the unique name constraint. Check Meta inheritance. |
| `django_tenant_options.W008` | Warning | Option model may be missing the tenant check constraint. Check Meta inheritance. |

### Selection model checks

| Check ID | Level | Description |
|----------|-------|-------------|
| `django_tenant_options.I004` | Info | Selection model manager doesn't inherit from `SelectionManager`. Filtering may not work as expected. |
| `django_tenant_options.E005` | Error | Selection model manager uses a queryset that doesn't inherit from `SelectionQuerySet`. |
| `django_tenant_options.E006` | Error | Selection model has no manager inheriting from `SelectionManager` with `SelectionQuerySet`. |
| `django_tenant_options.W009` | Warning | Selection model may be missing the `option_not_null` check constraint. |
| `django_tenant_options.W010` | Warning | Selection model may be missing the `tenant_not_null` check constraint. |
| `django_tenant_options.W011` | Warning | Selection model may be missing the `unique_active_selection` constraint. |

### Resolving check failures

**Error checks (E002, E003, E005, E006)**: Ensure your custom managers inherit from `OptionManager`/`SelectionManager` and your custom querysets inherit from `OptionQuerySet`/`SelectionQuerySet`.

**Warning checks (W007-W011)**: Ensure your model's `Meta` class inherits from `AbstractOption.Meta` or `AbstractSelection.Meta`:

```python
class MyOption(AbstractOption):
    class Meta(AbstractOption.Meta):  # This is required
        verbose_name = "My Option"
```

```{note}
Manager compliance checks (`I001`, `I004`, `E002`, `E005`) only run when `DEBUG = True`.
```

## Further reading

- [Models Guide](models.md) -- Using these settings in your models
- [Forms Guide](forms.md) -- Form-related settings in action
- [Customization](customization.md) -- Advanced configuration patterns
- [API Reference](reference.md) -- Auto-generated documentation from source
