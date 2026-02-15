# Models

This guide covers how to define and work with Option and Selection models in `django-tenant-options`.

## Defining an Option model

Create a concrete Option model by inheriting from `AbstractOption`:

```python
from django_tenant_options.models import AbstractOption
from django_tenant_options.choices import OptionType


class TaskPriorityOption(AbstractOption):
    tenant_model = "yourapp.Tenant"
    selection_model = "yourapp.TaskPrioritySelection"

    default_options = {
        "Critical": {"option_type": OptionType.OPTIONAL},
        "High": {"option_type": OptionType.MANDATORY},
        "Medium": {"option_type": OptionType.OPTIONAL},
        "Low": {},  # Defaults to OptionType.MANDATORY
    }

    class Meta(AbstractOption.Meta):
        verbose_name = "Task Priority Option"
        verbose_name_plural = "Task Priority Options"
```

### Required attributes

- **`tenant_model`** -- String path to your tenant model (e.g., `"myapp.Tenant"`). Can also be set globally via the `TENANT_MODEL` setting.
- **`selection_model`** -- String path to the paired Selection model (e.g., `"myapp.TaskPrioritySelection"`).

### The `default_options` dictionary

Each key is the option name. The value is a dictionary of configuration:

```python
default_options = {
    "Option Name": {
        "option_type": OptionType.MANDATORY,  # or OptionType.OPTIONAL
    },
    "Another Option": {},  # Empty dict defaults to OptionType.MANDATORY
}
```

- If `option_type` is omitted, it defaults to `OptionType.MANDATORY`.
- Only `OptionType.MANDATORY` and `OptionType.OPTIONAL` are valid here. `OptionType.CUSTOM` is for tenant-created options only.

### Meta class inheritance

Your `Meta` class **must** inherit from `AbstractOption.Meta`:

```python
class Meta(AbstractOption.Meta):
    verbose_name = "Task Priority Option"
```

This ensures database constraints (unique name constraint, tenant check constraint) are properly created. If you're using a custom base model like `auto_prefetch`, combine both Meta classes:

```python
class Meta(AbstractOption.Meta, auto_prefetch.Model.Meta):
    verbose_name = "Task Priority Option"
```

```{warning}
If your Meta class doesn't inherit from `AbstractOption.Meta`, you'll lose database constraints that protect data integrity. Django system checks (`W007`, `W008`) will warn you about this.
```

## Defining a Selection model

Create a concrete Selection model by inheriting from `AbstractSelection`:

```python
from django_tenant_options.models import AbstractSelection


class TaskPrioritySelection(AbstractSelection):
    tenant_model = "yourapp.Tenant"
    option_model = "yourapp.TaskPriorityOption"

    class Meta(AbstractSelection.Meta):
        verbose_name = "Task Priority Selection"
        verbose_name_plural = "Task Priority Selections"
```

### Required attributes

- **`tenant_model`** -- String path to your tenant model. Can also be set globally.
- **`option_model`** -- String path to the paired Option model.

### Meta class inheritance

Same rule as Options -- inherit from `AbstractSelection.Meta`:

```python
class Meta(AbstractSelection.Meta):
    verbose_name = "Task Priority Selection"
```

Missing this inheritance triggers system check warnings `W009`, `W010`, and `W011`.

## Using options in your business models

Add ForeignKey fields from your business models to the Option model:

```python
from django.db import models


class Task(models.Model):
    title = models.CharField(max_length=100)
    priority = models.ForeignKey(
        "yourapp.TaskPriorityOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    status = models.ForeignKey(
        "yourapp.TaskStatusOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
```

```{tip}
Using `on_delete=models.SET_NULL` with `null=True` is recommended. Since options use soft deletes, this prevents cascading deletions of your business data if an option is hard-deleted.
```

## Model relationships

The following diagram shows how the models relate to each other:

[![Model relationships diagram](https://mermaid.ink/img/pako:eNrFVcGOmzAQ_RXLe2lViEI2BLCilaqueumhlbK9VEiRYxyw1tjINu3SNP9eB0gIWWfVrioVLsO8mTdvzNjeQSIzChEkHGt9z3CucJkKYJ_WA95vtFGYmM-VYVIghHDv-NDCuy728CyXR-jubvC-WxnFRA4ELulzr2xZ16apzsF7bOgDKynIKKeGZmdQTs-aSEGU9a91vWlFUv3m7VlMlzVyEU6xGHk0_l4K2bsaXlkW8sqe_2sDD1RgYc5VvvwPrIhMlpgJB9dXTdWI6aNUlOXiE22Aaeu4BGD96CpvmOGO-hnVRLF2ENyFaivCjVSKScVMc0XElx7uZnckKWPE2MpbXHOz7qZQOxS3La5Lu0W4Y-GOE3IecFXEaZ6cS_NioX6XjKt0xnh7guUv33e1jgATBbUOPU4bRB3LHKDLZAd_CoMUAt-X1iqxaOzHNa4Ca3AIAaZQss6LnrMb2lfw_E3-aTVOIrrsdsyPub3RMyKwoVyKXAMjh_YH-lN8y_HH0VdVDSOdCm0aTi9_8ZZxjm62yeH1LCIfKbqJoqi3_R8sMwWaVU8ekVyqEZZhXWClcINACMLLAsPq_rsa0IMlVfZ0yewd0w5-Ck1B7TkEkTX7HZjCVOxtKK6NXDWCQGRUTT1YV5k9SftbCaIt5tp6Kyy-SVkeg-wnRDv4BFEwm02C-Xw6j4NgMY_iReDBBqJkPklub4M4moVJbOFw78GfLcF0EofJNFlEizAM4iCOw_1vIZE-UQ?type=png)](https://mermaid.live/edit#pako:eNrFVcGOmzAQ_RXLe2lViEI2BLCilaqueumhlbK9VEiRYxyw1tjINu3SNP9eB0gIWWfVrioVLsO8mTdvzNjeQSIzChEkHGt9z3CucJkKYJ_WA95vtFGYmM-VYVIghHDv-NDCuy728CyXR-jubvC-WxnFRA4ELulzr2xZ16apzsF7bOgDKynIKKeGZmdQTs-aSEGU9a91vWlFUv3m7VlMlzVyEU6xGHk0_l4K2bsaXlkW8sqe_2sDD1RgYc5VvvwPrIhMlpgJB9dXTdWI6aNUlOXiE22Aaeu4BGD96CpvmOGO-hnVRLF2ENyFaivCjVSKScVMc0XElx7uZnckKWPE2MpbXHOz7qZQOxS3La5Lu0W4Y-GOE3IecFXEaZ6cS_NioX6XjKt0xnh7guUv33e1jgATBbUOPU4bRB3LHKDLZAd_CoMUAt-X1iqxaOzHNa4Ca3AIAaZQss6LnrMb2lfw_E3-aTVOIrrsdsyPub3RMyKwoVyKXAMjh_YH-lN8y_HH0VdVDSOdCm0aTi9_8ZZxjm62yeH1LCIfKbqJoqi3_R8sMwWaVU8ekVyqEZZhXWClcINACMLLAsPq_rsa0IMlVfZ0yewd0w5-Ck1B7TkEkTX7HZjCVOxtKK6NXDWCQGRUTT1YV5k9SftbCaIt5tp6Kyy-SVkeg-wnRDv4BFEwm02C-Xw6j4NgMY_iReDBBqJkPklub4M4moVJbOFw78GfLcF0EofJNFlEizAM4iCOw_1vIZE-UQ)

![Model relationships detail](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Relationships-Detailed.png)

## Managers and querysets

The package automatically adds an `objects` manager and an `unscoped` manager to every Option and Selection model.

### OptionManager methods

Create options programmatically:

```python
# Create a custom option for a specific tenant
option = TaskPriorityOption.objects.create_for_tenant(
    tenant=my_tenant,
    name="Urgent",
)

# Create a mandatory default option
option = TaskPriorityOption.objects.create_mandatory(name="High")

# Create an optional default option
option = TaskPriorityOption.objects.create_optional(name="Medium")
```

### OptionQuerySet methods

Query options with tenant-aware filtering:

```python
# All options available to a tenant (mandatory + optional + tenant's custom)
TaskPriorityOption.objects.options_for_tenant(tenant)

# Only options the tenant has selected
TaskPriorityOption.objects.selected_options_for_tenant(tenant)

# Only active (non-deleted) options
TaskPriorityOption.objects.active()

# Only deleted options
TaskPriorityOption.objects.deleted()

# Only custom options (created by tenants)
TaskPriorityOption.objects.custom_options()
```

### SelectionManager methods

The Selection model's manager provides the same tenant-aware methods:

```python
# Options available to a tenant (through the selection model)
TaskPrioritySelection.objects.options_for_tenant(tenant)

# Currently selected options for a tenant
TaskPrioritySelection.objects.selected_options_for_tenant(tenant)
```

### The `unscoped` manager

Every model also has an `unscoped` manager that includes soft-deleted records:

```python
# Get all options, including deleted ones
TaskPriorityOption.unscoped.all()
```

Use this for administrative views or data cleanup tasks. The default `objects` manager excludes soft-deleted records.

## Soft delete operations

```python
# Soft delete (sets the `deleted` timestamp)
option.delete()

# Hard delete (actually removes from database)
option.delete(override=True)

# Restore a soft-deleted option
option.undelete()

# Bulk restore
TaskPriorityOption.unscoped.filter(deleted__isnull=False).undelete()
```

## Custom managers and querysets

If you need custom query methods, subclass the package's managers and querysets:

```python
from django_tenant_options.models import OptionQuerySet, OptionManager


class CustomOptionQuerySet(OptionQuerySet):
    def high_priority(self):
        return self.active().filter(name__in=["Critical", "High"])


class CustomOptionManager(OptionManager):
    def get_queryset(self):
        return CustomOptionQuerySet(self.model, using=self._db)


class TaskPriorityOption(AbstractOption):
    objects = CustomOptionManager()
    # ... rest of model definition
```

```{warning}
Custom managers **must** inherit from `OptionManager` (or `SelectionManager` for Selection models). Custom querysets **must** inherit from `OptionQuerySet` (or `SelectionQuerySet`). If they don't, the package's filtering methods won't be available, and Django system checks will flag the issue.
```

## Further reading

- [Concepts](concepts.md) -- Why the two-model pattern exists
- [Forms Guide](forms.md) -- Building forms that work with your models
- [Configuration Reference](configuration.md) -- Customizing model behavior through settings
