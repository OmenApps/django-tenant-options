# Usage Guide for django-tenant-options

## Installation

Install django-tenant-options using pip:

```bash
pip install django-tenant-options
```

## Basic Configuration

1. Add `django_tenant_options` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    ...
    'django_tenant_options',
    ...
]
```

2. Configure the required settings in your `settings.py`:

```python
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "yourapp.Tenant",  # Required

    # Optional settings with their defaults
    "TENANT_ON_DELETE": models.CASCADE,
    "OPTION_ON_DELETE": models.CASCADE,
    "TENANT_MODEL_RELATED_NAME": "%(app_label)s_%(class)s_related",
    "TENANT_MODEL_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss",
    "ASSOCIATED_TENANTS_RELATED_NAME": "%(app_label)s_%(class)s_selections",
    "ASSOCIATED_TENANTS_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss_selected",
    "OPTION_MODEL_RELATED_NAME": "%(app_label)s_%(class)s_related",
    "OPTION_MODEL_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss",
    "DB_VENDOR_OVERRIDE": None,
    "DISABLE_FIELD_FOR_DELETED_SELECTION": False,
}
```

## Core Concepts

### Option Types

django-tenant-options provides three types of options:

1. **Mandatory Options** (`OptionType.MANDATORY`):
   - Always available to all tenants
   - Cannot be disabled or removed by tenants
   - Example: Basic status options like "Active" or "Inactive"

2. **Optional Options** (`OptionType.OPTIONAL`):
   - Available to all tenants but can be enabled/disabled
   - Tenants choose whether to use them
   - Example: Additional status options like "On Hold" or "Under Review"

3. **Custom Options** (`OptionType.CUSTOM`):
   - Created by individual tenants
   - Only available to the tenant that created them
   - Example: Tenant-specific categories or statuses

## Model Configuration

### 1. Option Models

Create your Option model by inheriting from `AbstractOption`:

```python
from django_tenant_options.models import AbstractOption
from django_tenant_options.choices import OptionType

class TaskPriorityOption(AbstractOption):
    tenant_model = "yourapp.Tenant"  # Your tenant model
    selection_model = "yourapp.TaskPrioritySelection"

    # Define default options
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

### 2. Selection Models

Create your Selection model by inheriting from `AbstractSelection`:

```python
from django_tenant_options.models import AbstractSelection

class TaskPrioritySelection(AbstractSelection):
    tenant_model = "yourapp.Tenant"
    option_model = "yourapp.TaskPriorityOption"

    class Meta(AbstractSelection.Meta):
        verbose_name = "Task Priority Selection"
        verbose_name_plural = "Task Priority Selections"
```

### 3. Using Options in Your Models

Add ForeignKey fields to your models to use the options:

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
```

### Resulting Model Relationships

[![](https://mermaid.ink/img/pako:eNrFVcGOmzAQ_RXLe2lViEI2BLCilaqueumhlbK9VEiRYxyw1tjINu3SNP9eB0gIWWfVrioVLsO8mTdvzNjeQSIzChEkHGt9z3CucJkKYJ_WA95vtFGYmM-VYVIghHDv-NDCuy728CyXR-jubvC-WxnFRA4ELulzr2xZ16apzsF7bOgDKynIKKeGZmdQTs2aSEGU9a91vWlFUv3m7VlMlzVyEU6xGHk0_n4K2bsaXlkW8sqe_2sDD1RgYc5VvvwPrIhMlpgJB9dXTdWI6aNUlOXiE22Aaeu4BGD96CpvmOGO-hnVRLF2ENyFaivCjVSKScVMc0XElx7uZnckKWPE2MpbXHOz7qZQOxS3La5Lu0W4Y-GOE3IecFXEaZ6cS_NioX6XjKt0xnh7guUv33e1jgATBbUOPU4bRD3LHKDLZAd_CoMUAt-X1iqxaOzHNa4Ca3AIAaZQss6LnrMb2lfw_E3-aTVOIrrsdsyPub3RMyKwoVyKXAMjh_YH-lN8y_HH0VdVDSOdCm0aTi9_8ZZxjm62yeH1LCIfKbqJoqi3_R8sMwWaVU8ekVyqEZZhXWClcINACMLLAsPq_rsa0IMlVfZ0yewd0w5-Ck1B7TkEkTX7HZjCVOxtKK6NXDWCQGRUTT1YV5k9SftbCaIt5tp6Kyy-SVkeg-wnRDv4BFEwm02C-Xw6j4NgMY_iReDBBqJkPklub4M4moVJbOFw78GfLcF0EofJNFlEizAM4iCOw_1vIZE-UQ?type=png)](https://mermaid.live/edit#pako:eNrFVcGOmzAQ_RXLe2lViEI2BLCilaqueumhlbK9VEiRYxyw1tjINu3SNP9eB0gIWWfVrioVLsO8mTdvzNjeQSIzChEkHGt9z3CucJkKYJ_WA95vtFGYmM-VYVIghHDv-NDCuy728CyXR-jubvC-WxnFRA4ELulzr2xZ16apzsF7bOgDKynIKKeGZmdQTs2aSEGU9a91vWlFUv3m7VlMlzVyEU6xGHk0_n4K2bsaXlkW8sqe_2sDD1RgYc5VvvwPrIhMlpgJB9dXTdWI6aNUlOXiE22Aaeu4BGD96CpvmOGO-hnVRLF2ENyFaivCjVSKScVMc0XElx7uZnckKWPE2MpbXHOz7qZQOxS3La5Lu0W4Y-GOE3IecFXEaZ6cS_NioX6XjKt0xnh7guUv33e1jgATBbUOPU4bRD3LHKDLZAd_CoMUAt-X1iqxaOzHNa4Ca3AIAaZQss6LnrMb2lfw_E3-aTVOIrrsdsyPub3RMyKwoVyKXAMjh_YH-lN8y_HH0VdVDSOdCm0aTi9_8ZZxjm62yeH1LCIfKbqJoqi3_R8sMwWaVU8ekVyqEZZhXWClcINACMLLAsPq_rsa0IMlVfZ0yewd0w5-Ck1B7TkEkTX7HZjCVOxtKK6NXDWCQGRUTT1YV5k9SftbCaIt5tp6Kyy-SVkeg-wnRDv4BFEwm02C-Xw6j4NgMY_iReDBBqJkPklub4M4moVJbOFw78GfLcF0EofJNFlEizAM4iCOw_1vIZE-UQ)

## Form Implementation

### 1. User-Facing Forms

For forms that allow users to select from tenant-specific options:

```python
from django import forms
from django_tenant_options.forms import UserFacingFormMixin

class TaskForm(UserFacingFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "priority"]
```

### 2. Option Management Forms

For forms that allow tenants to create and manage custom options:

```python
from django import forms
from django_tenant_options.forms import (
    OptionCreateFormMixin,
    OptionUpdateFormMixin,
)

class TaskPriorityCreateForm(OptionCreateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = ["name"]

class TaskPriorityUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = ["name"]
```

### 3. Selection Management Forms

For forms that allow tenants to manage which options are available:

```python
from django_tenant_options.forms import SelectionForm

class TaskPrioritySelectionForm(SelectionForm):
    class Meta:
        model = TaskPrioritySelection
```

## View and Template Integration

### 1. Views

```python
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs

class TaskPriorityOptionCreateView(LoginRequiredMixin, CreateView):
    model = TaskPriorityOption
    form_class = TaskPriorityCreateForm
    template_name = "tasks/priority_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs
```

### 2. Templates

```html
<!-- tasks/task_form.html -->
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Save Task</button>
</form>

<!-- tasks/priority_list.html -->
<h2>Task Priorities</h2>
<ul>
{% for priority in priorities %}
    <li>
        {{ priority.name }}
        {% if priority.option_type == 'dm' %}
            (Mandatory)
        {% elif priority.option_type == 'do' %}
            (Optional)
        {% else %}
            (Custom)
        {% endif %}
    </li>
{% endfor %}
</ul>
```

## Database Operations

### 1. Creating Database Triggers

After setting up your models, create database triggers to ensure referential integrity:

```bash
python manage.py maketriggers
python manage.py migrate
```

### 2. Synchronizing Default Options

After updating default options in your models:

```bash
python manage.py syncoptions
```

## Management Commands

### 1. List Options

To view all options in the database:

```bash
python manage.py listoptions
```

### 2. Making Triggers

Create database triggers with various options:

```bash
# Create triggers for all models
python manage.py maketriggers

# Create triggers for a specific app
python manage.py maketriggers --app yourapp

# Create triggers for a specific model
python manage.py maketriggers --model yourapp.TaskPriorityOption

# Force recreation of existing triggers
python manage.py maketriggers --force

# Preview trigger creation without making changes
python manage.py maketriggers --dry-run --verbose
```

## Advanced Configuration

### 1. Custom Form Fields

You can customize how options are displayed in forms:

```python
from django_tenant_options.form_fields import OptionsModelMultipleChoiceField

class CustomOptionsField(OptionsModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} - {obj.get_option_type_display()}"

DJANGO_TENANT_OPTIONS = {
    "DEFAULT_MULTIPLE_CHOICE_FIELD": CustomOptionsField,
}
```

### 2. Custom Managers and QuerySets

Extend the default managers and querysets for additional functionality:

```python
from django_tenant_options.models import OptionQuerySet, OptionManager

class CustomOptionQuerySet(OptionQuerySet):
    def active_mandatory(self):
        return self.active().filter(option_type="dm")

class CustomOptionManager(OptionManager):
    def get_queryset(self):
        return CustomOptionQuerySet(self.model, using=self._db)

class TaskPriorityOption(AbstractOption):
    objects = CustomOptionManager()
    # ... rest of the model definition
```

### Performance Optimization

1. **Querying Efficiency**
   ```python
   # Use select_related for foreign keys
   TaskPriorityOption.objects.select_related('tenant').all()
   ```

2. **Caching**
   ```python
   # Cache frequently used options
   from django.core.cache import cache

   def get_tenant_options(tenant):
       cache_key = f"tenant_{tenant.id}_options"
       options = cache.get(cache_key)
       if options is None:
           options = list(tenant.options.active())
           cache.set(cache_key, options, timeout=3600)
       return options
   ```

For more information on the available settings, see the [`app_settings.py` reference](https://django-tenant-options.readthedocs.io/en/latest/reference.html#module-django_tenant_options.app_settings).
