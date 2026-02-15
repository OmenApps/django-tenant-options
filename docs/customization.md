# Customization

This guide covers advanced customization: custom querysets and managers, custom form fields, base class configuration, database triggers, and performance tips.

## Custom querysets and managers

Extend the package's querysets and managers to add domain-specific query methods.

### Custom queryset

```python
from django_tenant_options.models import OptionQuerySet, OptionManager


class PriorityOptionQuerySet(OptionQuerySet):
    def critical_only(self):
        return self.active().filter(name__icontains="critical")

    def active_priority(self):
        return self.active().filter(priority_weight__gt=0)
```

### Custom manager

```python
class PriorityOptionManager(OptionManager):
    def get_queryset(self):
        return PriorityOptionQuerySet(self.model, using=self._db)
```

### Using them in your model

```python
class TaskPriorityOption(AbstractOption):
    objects = PriorityOptionManager()
    priority_weight = models.IntegerField(default=0)

    tenant_model = "yourapp.Tenant"
    selection_model = "yourapp.TaskPrioritySelection"
    # ...
```

```{important}
Custom managers must inherit from `OptionManager` (for Option models) or `SelectionManager` (for Selection models). Custom querysets must inherit from `OptionQuerySet` or `SelectionQuerySet`. System checks will flag incorrect inheritance.
```

## Custom form fields

Customize how options appear in `SelectionsForm` by subclassing `OptionsModelMultipleChoiceField`:

```python
from django_tenant_options.form_fields import OptionsModelMultipleChoiceField


class CustomOptionsField(OptionsModelMultipleChoiceField):
    def label_from_instance(self, obj):
        label = obj.name
        if obj.option_type == "dm":
            label += " [Required]"
        elif obj.option_type == "do":
            label += " [Available]"
        else:
            label += " [Custom]"
        return label
```

Configure globally in settings:

```python
DJANGO_TENANT_OPTIONS = {
    "DEFAULT_MULTIPLE_CHOICE_FIELD": "yourapp.forms.CustomOptionsField",
}
```

Or set it per-form by overriding `multiple_choice_field_class` before the `SelectionsForm` initializes its fields.

## Base class configuration

The package allows you to replace the default Django base classes used internally. This is useful when integrating with packages like [django-auto-prefetch](https://github.com/tolomea/django-auto-prefetch) that provide optimized base classes.

### Configuration through settings

```python
import auto_prefetch

DJANGO_TENANT_OPTIONS = {
    "MODEL_CLASS": auto_prefetch.Model,            # Default: django.db.models.Model
    "MANAGER_CLASS": "auto_prefetch.Manager",      # Default: django.db.models.Manager
    "QUERYSET_CLASS": "auto_prefetch.QuerySet",    # Default: django.db.models.QuerySet
    "FOREIGNKEY_CLASS": auto_prefetch.ForeignKey,   # Default: django.db.models.ForeignKey
    "ONETOONEFIELD_CLASS": "auto_prefetch.OneToOneField",  # Default: django.db.models.OneToOneField
}
```

Values can be actual class references or dotted string paths.

### Programmatic configuration

For more granular control:

```python
from django_tenant_options.app_settings import model_config

model_config.model_class = "auto_prefetch.Model"
model_config.manager_class = auto_prefetch.Manager
model_config.queryset_class = auto_prefetch.QuerySet
model_config.foreignkey_class = auto_prefetch.ForeignKey
model_config.onetoonefield_class = "auto_prefetch.OneToOneField"
```

### Meta class with custom base models

When using a custom base model class that has its own Meta, combine both in your model's Meta:

```python
class TaskPriorityOption(AbstractOption):
    class Meta(AbstractOption.Meta, auto_prefetch.Model.Meta):
        verbose_name = "Task Priority Option"
```

## Database triggers

Database triggers provide an additional layer of referential integrity enforcement at the database level.

### What they protect

Triggers ensure that a Selection's tenant always matches the Option's tenant (for custom options) or that the Option is a default option. This prevents mismatches that could occur from:

- Direct SQL operations bypassing Django's ORM
- Race conditions in concurrent operations
- Bugs in custom code that skip model validation

### Supported databases

| Database   | Support |
|-----------|---------|
| PostgreSQL | Full    |
| MySQL      | Full    |
| SQLite     | Full    |
| Oracle     | Full    |

### Custom database backends

If you use a custom backend (e.g., PostGIS) built on a supported database, override the vendor detection:

```python
DJANGO_TENANT_OPTIONS = {
    "DB_VENDOR_OVERRIDE": "postgresql",
}
```

Or pass it per-command:

```bash
python manage.py maketriggers --db-vendor-override postgresql
```

### Regenerating triggers

If you change your model structure, regenerate triggers:

```bash
python manage.py maketriggers --force
python manage.py migrate
```

## Performance tips

### Use `select_related` for ForeignKey queries

When querying models with ForeignKey fields to Option models:

```python
tasks = Task.objects.select_related("priority", "status").all()
```

### Cache frequently accessed options

Options don't change often. Cache them to avoid repeated database queries:

```python
from django.core.cache import cache


def get_tenant_options(tenant):
    cache_key = f"tenant_{tenant.id}_options"
    options = cache.get(cache_key)
    if options is None:
        options = list(TaskPriorityOption.objects.selected_options_for_tenant(tenant))
        cache.set(cache_key, options, timeout=3600)
    return options
```

Remember to invalidate the cache when selections change (e.g., in a post-save signal or after `SelectionsForm.save()`).

### Consider auto_prefetch

If your application has many ForeignKey lookups, the [django-auto-prefetch](https://github.com/tolomea/django-auto-prefetch) package can automatically optimize queries. Configure it using the base class settings described above.

## Further reading

- [Models Guide](models.md) -- Foundational model concepts
- [Configuration Reference](configuration.md) -- All available settings
- [Commands](commands.md) -- The `maketriggers` and `removetriggers` commands
