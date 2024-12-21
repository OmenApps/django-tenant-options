# Usage Guide

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

Only the `TENANT_MODEL` setting is required. The other settings have default values that can be overridden if needed for advanced customization.

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

See the [Configuration Guide](https://django-tenant-options.readthedocs.io/en/latest/usage.html#configuration-guide) for more details on available settings.

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

> ⚠️ Warning
>
> The package automatically adds an `objects` Manager and associated QuerySet to each option and selection model. If you define a custom Manager or QuerySet, ensure it inherits from `OptionManager` or `OptionQuerySet`, or your optyions and selections will not work as intended. Also, an additional `unscoped` Manager is available for querying all options, including soft-deleted ones.

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
  {% csrf_token %} {{ form.as_p }}
  <button type="submit">Save Task</button>
</form>

<!-- tasks/priority_list.html -->
<h2>Task Priorities</h2>
<ul>
  {% for priority in priorities %}
  <li>
    {{ priority.name }} {% if priority.option_type == 'dm' %} (Mandatory) {%
    elif priority.option_type == 'do' %} (Optional) {% else %} (Custom) {% endif
    %}
  </li>
  {% endfor %}
</ul>
```

## Database Operations

### 1. Creating Database Triggers

`django-tenant-options` can automatically create database triggers migrations for referential integrity.

To do this, after setting up your models, run the following commands:

```bash
python manage.py maketriggers
python manage.py migrate
```

### 2. Removing Database Triggers

`django-tenant-options` can also remove the database triggers if needed. New migrations will be created to reflect the changes.

To remove database triggers, run the following command:

```bash
python manage.py removetriggers
python manage.py migrate
```

### 3. Synchronizing Default Options

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

## Configuration Guide

### Basic Configuration

Django Tenant Options can be configured through your Django settings. Add a `DJANGO_TENANT_OPTIONS` dictionary to your settings:

```python
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "myapp.Tenant",
    # ... other settings
}
```

### Base Model Classes

Django Tenant Options allows you to customize the base classes used for models, managers, querysets and field types. This is particularly useful when integrating with packages like django-auto-prefetch or implementing custom behavior across all tenant option models.

#### Configuration Through Settings

Configure base classes globally in your Django settings:

```python
DJANGO_TENANT_OPTIONS = {
    # Base class settings
    "MODEL_CLASS": "auto_prefetch.Model",  # Default: django.db.models.Model
    "MANAGER_CLASS": "auto_prefetch.Manager",  # Default: django.db.models.Manager
    "QUERYSET_CLASS": "auto_prefetch.QuerySet",  # Default: django.db.models.QuerySet
    "FOREIGNKEY_CLASS": "auto_prefetch.ForeignKey",  # Default: django.db.models.ForeignKey
    "ONETOONEFIELD_CLASS": "auto_prefetch.OneToOneField",  # Default: django.db.models.OneToOneField
}
```

#### Programmatic Configuration

For more granular control, you can configure base classes programmatically:

```python
from django_tenant_options.app_settings import model_config
import auto_prefetch

# Configure base classes
model_config.model_class = auto_prefetch.Model
model_config.manager_class = auto_prefetch.Manager
model_config.queryset_class = auto_prefetch.QuerySet
model_config.foreignkey_class = auto_prefetch.ForeignKey
model_config.onetoonefield_class = auto_prefetch.OneToOneField
```

### Model Configuration

#### Tenant Model Settings

```python
DJANGO_TENANT_OPTIONS = {
    # Required: Specify your tenant model
    "TENANT_MODEL": "myapp.Tenant",  # Default: "django_tenant_options.Tenant"

    # What happens when a tenant is deleted
    "TENANT_ON_DELETE": "models.CASCADE",  # Default: models.CASCADE

    # Related name templates for tenant relationships
    "TENANT_MODEL_RELATED_NAME": "%(app_label)s_%(class)s_related",
    "TENANT_MODEL_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss",
}
```

#### Option Model Settings

```python
DJANGO_TENANT_OPTIONS = {
    # What happens when an option is deleted
    "OPTION_ON_DELETE": "models.CASCADE",  # Default: models.CASCADE

    # Related name templates for option relationships
    "OPTION_MODEL_RELATED_NAME": "%(app_label)s_%(class)s_related",
    "OPTION_MODEL_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss",

    # Templates for the many-to-many relationship between options and tenants
    "ASSOCIATED_TENANTS_RELATED_NAME": "%(app_label)s_%(class)s_selections",
    "ASSOCIATED_TENANTS_RELATED_QUERY_NAME": "%(app_label)s_%(class)ss_selected",
}
```

#### Database Configuration

```python
DJANGO_TENANT_OPTIONS = {
    # Override database vendor detection
    "DB_VENDOR_OVERRIDE": "postgresql",  # Options: 'postgresql', 'mysql', 'sqlite', 'oracle'
}
```

This setting is useful when using custom database backends (e.g., PostGIS) while the underlying database is a supported vendor.

### Form Configuration

```python
DJANGO_TENANT_OPTIONS = {
    # Default form field for multiple choice fields
    "DEFAULT_MULTIPLE_CHOICE_FIELD": "myapp.CustomOptionsField",  # Default: OptionsModelMultipleChoiceField

    # Control behavior of deleted selections in forms
    "DISABLE_FIELD_FOR_DELETED_SELECTION": False,  # Default: False
}
```

When `DISABLE_FIELD_FOR_DELETED_SELECTION` is True, deleted selections appear disabled in forms rather than requiring selection of a new option.

## Extending Models and Queries

### Custom Form Fields

You can customize how options are displayed in forms by subclassing `OptionsModelMultipleChoiceField`:

```python
from django_tenant_options.form_fields import OptionsModelMultipleChoiceField

class CustomOptionsField(OptionsModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} - {obj.get_option_type_display()}"
```

### Extending QuerySets and Managers

Add custom functionality by subclassing the base querysets and managers:

```python
from django_tenant_options.models import OptionQuerySet, OptionManager

class CustomOptionQuerySet(OptionQuerySet):
    def active_priority(self):
        return self.active().filter(priority__gt=0)

class CustomOptionManager(OptionManager):
    def get_queryset(self):
        return CustomOptionQuerySet(self.model, using=self._db)

class PriorityOption(AbstractOption):
    objects = CustomOptionManager()
    priority = models.IntegerField(default=0)
```

### Performance Optimization

1. **Querying Efficiency**

   ```python
   # Use select_related for foreign keys
   TaskPriorityOption.objects.select_related('tenant').all()
   ```

2. **Caching**

*We are in the process of adding caching support to the package. In the meantime, you can implement your own caching mechanism:*

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

## Local Development

### Setting Up Your Development Environment

1. Clone the repository:

```bash
git clone https://github.com/OmenApps/django-tenant-options.git
cd django-tenant-options
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

3. Install development dependencies using `uv`:

```bash
pip install uv
uv sync --prerelease=allow --extra=dev
```

### Example Project

The repository includes an example project that demonstrates the package's functionality. Since migrations aren't included, you'll need to create them:

```bash
cd example_project
python manage.py makemigrations
python manage.py migrate
```

### Using Nox for Development Tasks

We use Nox for automated testing and development tasks. Our `noxfile.py` includes several useful sessions:

```bash
# List all available Nox sessions
nox --list

# Run all default sessions
nox

# Run specific sessions
nox -s pre-commit        # Run pre-commit checks
nox -s safety           # Check dependencies for security issues
nox -s tests           # Run test suite
nox -s xdoctest        # Run examples in docstrings
nox -s docs-build      # Build documentation
nox -s docs            # Serve documentation with live reload
```

#### Running Tests

Tests can be run against different Python and Django versions:

```bash
# Run tests with default Python/Django versions
nox -s tests

# Run tests with specific Python/Django versions
nox -s tests -- python="3.12" django="5.1"

# Run specific test file
nox -s tests -- example_project/tests/test_models.py

# Run with pytest options
nox -s tests -- -v --pdb
```

#### Building Documentation

For documentation development:

```bash
# Build docs once
nox -s docs-build

# Serve docs with live reload
nox -s docs

# Build docs for specific Django version
nox -s docs-build -- django="5.1"
```

#### Code Quality Checks

```bash
# Run all pre-commit hooks
nox -s pre-commit

# Run security checks
nox -s safety

# Run example tests
nox -s xdoctest
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them with:

```bash
nox -s pre-commit -- install
```

This will set up the following hooks:

- Black (code formatting)
- isort (import sorting)
- Flake8 (code linting)
- Various other code quality checks

### Database Configuration

By default, the example project uses SQLite. For development with other databases:

```python
# example_project/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tenant_options_dev',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Creating Database Triggers

After setting up your database and running migrations, create database triggers, if desired:

```bash
python manage.py maketriggers
python manage.py migrate
```

### Workflow Tips

1. **Branch Management**

   - Create feature branches from `main`
   - Use descriptive branch names (e.g., `feature/add-new-option-type`)
   - Keep branches up to date with `main`

2. **Testing**

   - Write tests for new features
   - Run the full test suite before submitting PRs
   - Test with multiple Python/Django versions using Nox

3. **Documentation**

   - Update docs for new features
   - Run docs locally to preview changes
   - Include docstrings for new code

4. **Code Quality**
   - Run pre-commit hooks before committing
   - Address all linting issues
   - Follow the existing code style

### Common Issues and Solutions

1. **Database Trigger Conflicts**

   ```bash
   # If you encounter trigger conflicts, force recreate them
   python manage.py maketriggers --force
   python manage.py migrate
   ```

2. **Pre-commit Hook Failures**

   ```bash
   # Re-run failed hooks
   pre-commit run --all-files

   # Update pre-commit hooks
   pre-commit autoupdate
   ```

3. **Documentation Build Errors**
   ```bash
   # Clean and rebuild
   rm -rf docs/_build
   nox -s docs-build
   ```

### Additional Resources

- Check the [Contributing Guide](https://django-tenant-options.readthedocs.io/en/latest/contributing.html) for detailed contribution guidelines
- Review our [Code of Conduct](https://django-tenant-options.readthedocs.io/en/latest/codeofconduct.html)
- Join discussions in the [GitHub Issues](https://github.com/OmenApps/django-tenant-options/issues) section

### Submitting Changes

1. Ensure all tests pass:

   ```bash
   nox -s tests
   ```

2. Build and check documentation:

   ```bash
   nox -s docs-build
   ```

3. Run all quality checks:

   ```bash
   nox -s pre-commit -- run --all-files
   ```

4. Create a pull request with:
   - Clear description of changes
   - Any related issue numbers
   - Notes about breaking changes
   - Updates to documentation
