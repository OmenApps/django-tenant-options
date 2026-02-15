# Quick Start

Get `django-tenant-options` running in your existing Django project.

## Install the package

```bash
pip install django-tenant-options
```

## Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    "django_tenant_options",
    ...
]
```

## Configure your tenant model

Add this to your `settings.py`. The `TENANT_MODEL` setting is the only one required:

```python
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "yourapp.Tenant",
}
```

Your project needs a tenant model -- any Django model that represents an organization, team, or account in your SaaS application. If you already have one, point `TENANT_MODEL` at it. If not, create a simple one:

```python
from django.db import models

class Tenant(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
```

## Create your first Option and Selection models

Each set of customizable options needs two models: an **Option** model (stores all available choices) and a **Selection** model (tracks which options each tenant has enabled).

```python
from django_tenant_options.models import AbstractOption, AbstractSelection
from django_tenant_options.choices import OptionType


class TaskPriorityOption(AbstractOption):
    tenant_model = "yourapp.Tenant"
    selection_model = "yourapp.TaskPrioritySelection"

    default_options = {
        "High": {},                                      # Mandatory by default
        "Medium": {"option_type": OptionType.OPTIONAL},  # Tenants choose whether to use this
        "Low": {},                                       # Mandatory by default
    }

    class Meta(AbstractOption.Meta):
        verbose_name = "Task Priority Option"
        verbose_name_plural = "Task Priority Options"


class TaskPrioritySelection(AbstractSelection):
    tenant_model = "yourapp.Tenant"
    option_model = "yourapp.TaskPriorityOption"

    class Meta(AbstractSelection.Meta):
        verbose_name = "Task Priority Selection"
        verbose_name_plural = "Task Priority Selections"
```

```{important}
Your `Meta` class **must** inherit from `AbstractOption.Meta` or `AbstractSelection.Meta`. Without this, database constraints that protect your data won't be created.
```

## Run migrations and sync options

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py syncoptions
```

The `syncoptions` command creates the default option records ("High", "Medium", "Low") in your database. Run it whenever you change `default_options` in your models.

## Verify it worked

```bash
python manage.py listoptions
```

You should see your default options listed with their types (Mandatory/Optional).

## Use options in your models

Add a ForeignKey from your business model to the Option model:

```python
class Task(models.Model):
    title = models.CharField(max_length=100)
    priority = models.ForeignKey(
        "yourapp.TaskPriorityOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
```

## Use options in your forms

The `UserFacingFormMixin` automatically filters option choices to show only what the current tenant has selected:

```python
from django import forms
from django_tenant_options.forms import UserFacingFormMixin

class TaskForm(UserFacingFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "priority"]
```

Every form using this mixin requires a `tenant` argument from your view:

```python
form = TaskForm(request.POST, tenant=request.user.tenant)
```

## What's next

- [Tutorial](tutorial.md) -- Build a complete task manager with tenant-specific options step by step
- [Models Guide](models.md) -- Detailed model configuration, managers, and querysets
- [Forms Guide](forms.md) -- All form mixins and fields explained
- [Configuration Reference](configuration.md) -- Every available setting
