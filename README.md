# django-tenant-options

[![PyPI](https://img.shields.io/pypi/v/django-tenant-options.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/django-tenant-options.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/django-tenant-options)][pypi status]
[![License](https://img.shields.io/pypi/l/django-tenant-options)][license]

[![Read the documentation at https://django-tenant-options.readthedocs.io/](https://img.shields.io/readthedocs/django-tenant-options/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Tests](https://github.com/OmenApps/django-tenant-options/actions/workflows/tests.yml/badge.svg)][tests]
[![Codecov](https://codecov.io/gh/OmenApps/django-tenant-options/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]
[![Published on Django Packages](https://img.shields.io/badge/Published%20on-Django%20Packages-0c3c26)](https://djangopackages.org/packages/p/django-tenant-options/)

[pypi status]: https://pypi.org/project/django-tenant-options/
[read the docs]: https://django-tenant-options.readthedocs.io/
[tests]: https://github.com/jacklinke/django-tenant-options/actions?workflow=Tests
[codecov]: https://app.codecov.io/gh/jacklinke/django-tenant-options
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

**Empowering Your SaaS Tenants with Custom Options and Sane Defaults**

## So your SaaS tenants want to provide end users with choices in a form...

_How can you implement this?_

- **CharField with TextChoices or IntegerChoices**: Define a fixed set of options in your model.
  - ❌ One size fits all
  - ❌ No customization for tenants
  - ❌ Code changes required for new options
- **ManyToManyField with a custom model**: Create a custom model to store options and use a ManyToManyField in your form.
  - ❌ No distinction between tenant options
  - ❌ Complex to manage defaults
  - ❌ Hard to maintain consistency
- **JSON Fields**: Store custom options as JSON in a single field.
  - ❌ No schema validation
  - ❌ No referential integrity
- **Custom Tables Per Tenant**
  - ❌ Schema complexity
  - ❌ Migration nightmares
  - ❌ Performance issues
- **django-tenant-options**:
  - ✅ Structured and flexible
  - ✅ Allows tenants to define their own sets of values for form inputs
  - ✅ Allows you, the developer, to offer global defaults (both mandatory and optional)

In a SaaS environment, one size doesn't fit all. Tenants often have unique needs for the choices they offer in user-facing forms, but building an entirely custom solution for each tenant - or requiring each tenant to define their own options from scratch - can be complex and time-consuming.

## Key Features

- **Customizable Options**: Allow tenants to define their own sets of values for form input while still offering global defaults.
- **Mandatory and Optional Defaults**: Define which options are mandatory for all tenants and which can be optionally used by tenants in their forms.
- **Seamless Integration**: Works with your existing Django models, making it easy to integrate into your project.
- **Tenant-Specific Logic**: Built-in support for tenant-specific logic, so each tenant’s unique needs can be met.

## Potential Use-Cases

`django-tenant-options` is versatile and can be applied to a wide range of scenarios across different industries. Here are some examples to illustrate its utility:

### 1. Project Management for Engineering Firms

**Scenario**: A Django-based project management tool used by multiple engineering firms.

- **Tenant Structure**: Each engineering firm acts as a tenant, with employees as end-users.
- **Implementation**: The app developer sets mandatory task statuses like "Assigned" and "Completed" for all firms. Each firm can then choose whether to include optional statuses like "In Review" or "Pending Approval," and even create their own unique statuses to fit their workflow. Likewise, the developer can provide mandatory task priorities like "High" and "Low," with firms able to add optional priorities like "Urgent" or "Deferred."

### 2. HR Management System

**Scenario**: An HR management system used within a large organization.

- **Tenant Structure**: The HR department is the tenant, and different departments within the organization are the end-users.
- **Implementation**: Mandatory job titles like "Manager" or "Team Lead" are predefined by the developer. The HR department can choose whether to include optional titles that were provided by the developer, and can create custom roles titles specific to their organizational structure.

### 3. Real Estate Management

**Scenario**: A property management tool for real estate companies.

- **Tenant Structure**: Real estate companies are tenants, and agents are the end-users.
- **Implementation**: Some property types like "Residential" are mandatorily available to agents in all companies. Companies can choose to make optional property types like "Commercial" available, and can also create custom categories like "Luxury" or "Affordable Housing" to match market segments.

### 4. Municipal Building Permit Management

**Scenario**: A system for managing building permits in various municipalities.

- **Tenant Structure**: Municipalities are tenants, and residents or businesses are the end-users.
- **Implementation**: Each municipality has mandatory permit types, required by Federal or State law, but they can also offer optional and custom permit types specific to local regulations.

### 5. Other Use-Cases

See [the options cookbook](https://django-tenant-options.readthedocs.io/en/latest/optionscookbook.html) in the documentation for more inspiration.

## Example Implementation

Consider a scenario where your SaaS provides project management tools for businesses. Each User is associated with a Tenant, and can create Tasks. You want each tenant to be able to customize the available task "priorities" and "status" provided in user-facing task tracking forms. Here’s how you can implement this with `django-tenant-options`.

> 🟩 Note
>
> See the [example project](https://django-tenant-options.readthedocs.io/en/latest/exampleproject.html) for the more detailed demonstration of how to set up a multi-tenant application with custom options using `django-tenant-options`.

### Existing Models

We will define a very basic `Tenant` model and a `Task` model to illustrate the implementation. You can adapt this to your project's models as needed. In this example, it is assumed that the project already has a `User` model and the `User` model has a `ForeignKey` to the `Tenant` model. Your project's tenant architecture may (and probably will) differ.

```python
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Tenant(models.Model):
    """A very simplistic example of how one might implement a Tenant architecture."""
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    """A very simplistic example of a Task model."""

    title = models.CharField(max_length=100)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
```

### Customizable Task Priorities

Each Set of options in `django-tenant-options` is defined by two models: an `Option` model, which stores all mandatory, optional, and custom options, and a `Selection` model, which identifies which options are currently associated with a tenant.

With a `Tenant` model and a `Task` model in your project, you can implement the `TaskPriorityOption` and `TaskPrioritySelection` models, which inherit from [`AbstractOption`](https://django-tenant-options.readthedocs.io/en/latest/reference.html#django_tenant_options.models.AbstractOption) and [`AbstractSelection`](https://django-tenant-options.readthedocs.io/en/latest/reference.html#django_tenant_options.models.AbstractSelection) respectively.

In each Option model, you can define the `default_options` dictionary for task priorities or status, including which options are mandatory and which are optional. In this example, "High" and "Low" priorities are mandatory for all tenants (and users will always see these options in forms), while "Critical" and "Medium" priorities are optional for selection by tenants. Tenants can also create custom priorities as needed.

```python
from django.db import models

from django_tenant_options.models import AbstractOption, AbstractSelection
from django_tenant_options.choices import OptionType


class TaskPriorityOption(AbstractOption):
    """Concrete implementation of AbstractOption for TaskPriority."""
    tenant_model = "example.Tenant"  # Can be defined in settings.py for global use
    selection_model = "example.TaskPrioritySelection"
    default_options = {
        "Critical": {"option_type": OptionType.OPTIONAL},
        "High": {"option_type": OptionType.MANDATORY},
        "Medium": {"option_type": OptionType.OPTIONAL},
        "Low": {},  # If no option_type is provided, it defaults to OptionType.MANDATORY
    }

    class Meta(AbstractOption.Meta):
        verbose_name = "Task Priority Option"
        verbose_name_plural = "Task Priority Options"


class TaskPrioritySelection(AbstractSelection):
    """Concrete implementation of AbstractSelection for TaskPriority."""
    tenant_model = "example.Tenant"  # Can be defined in settings.py for global use
    option_model = "example.TaskPriorityOption"

    class Meta(AbstractSelection.Meta):
        verbose_name = "Task Priority Selection"
        verbose_name_plural = "Task Priority Selections"
```

In each tenant's forms, the "High" and "Low" priorities will always be available for users to select in forms. Each tenant can also choose whether to make "Critical" and "Medium" priorities available to users, and they can create new priorities to meet their needs, offering a balance between predefined options and tenant-specific customization.

Finally, add `priority` and `status` ForeignKey fields on the `Task` model to the `TaskPriorityOption` and `TaskStatusOption` models respectively, allowing users to select from the various task priorities available to the tenant they belong to.

```python
from django.contrib.auth import get_user_model
from django.db import models

from example.models import TaskPriorityOption, TaskStatusOption, User

User = get_user_model()


class Tenant(models.Model):
    """A very simplistic example of how one might implement a Tenant architecture."""
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    """A very simplistic example of a Task model with priority and status."""

    title = models.CharField(max_length=100)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")

    priority = models.ForeignKey(
        "example.TaskPriorityOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    status = models.ForeignKey(
        "example.TaskStatusOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
```

### Forms

`django-tenant-options` provides a set of form mixins and fields to manage the options and selections for each tenant.

You can use these forms in your views to allow tenants to customize their options.

- `OptionCreateFormMixin` and `OptionUpdateFormMixin` are provided to create and update Options.
- `SelectionForm` is used to manage the Selections associated with a tenant.
- `UserFacingFormMixin` is provided to ensures ForeignKey fields to an `AbstractOption` subclass are populated with the correct tenant Selections.
- `OptionsModelMultipleChoiceField` is a customized `ModelMultipleChoiceField` that retrieves the Options and also displays the option type associated with each Option.

You are encouraged to extend these Mixins and Fields to suit your project's needs.

```python
from django import forms

from django_tenant_options.forms import OptionCreateFormMixin, OptionUpdateFormMixin, SelectionForm, UserFacingFormMixin
from example.models import Task, TaskPriorityOption, TaskPrioritySelection


class TaskForm(UserFacingFormMixin, forms.ModelForm):
    """Form for creating and updating a Task."""
    class Meta:
        model = Task
        fields = "__all__"


class TaskPriorityOptionCreateForm(OptionCreateFormMixin, forms.ModelForm):
    """Form for creating a TaskPriorityOption."""
    class Meta:
        model = TaskPriorityOption
        fields = "__all__"


class TaskPriorityOptionUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
    """Form for updating a TaskPriorityOption."""
    class Meta:
        model = TaskPriorityOption
        fields = "__all__"


class TaskPrioritySelectionForm(SelectionForm):
    """Form for selecting TaskPriorityOptions."""
    class Meta:
        model = TaskPrioritySelection
```

### Views, Templates, and URLs

Views, Templates, and URLs can be implemented as needed to allow tenants to manage their options. Views tfor forms that use `OptionCreateFormMixin`, `OptionUpdateFormMixin`, and `SelectionForm` must pass the tenant instance to the form's `tenant` attribute.

## Settings

`django-tenant-options` provides a number of settings to configure the behavior of the package. For details on all available settings, see the [App Settings Reference](https://django-tenant-options.readthedocs.io/en/latest/reference.html#module-django_tenant_options.app_settings).

## Management Commands

`django-tenant-options` provides management commands for easy maintenance:

- **[`listoptions`](https://django-tenant-options.readthedocs.io/en/latest/reference.html#listoptions)**: Lists all available options in the database.
- **[`syncoptions`](https://django-tenant-options.readthedocs.io/en/latest/reference.html#syncoptions)**: Synchronizes the `default_options` in each model with the database when a change in the model has been made. Should always be run after any migrations have been completed.
- **[`maketriggers`](https://django-tenant-options.readthedocs.io/en/latest/reference.html#maketriggers-options)**: Creates database trigger migrations to ensure there can never be mismatch between a Tenant and an associated Option.

```bash
python manage.py syncoptions
```

## Conclusion

`django-tenant-options` makes it easy to provide your SaaS application’s tenants with customizable form options, while maintaining consistency and control.

Explore the [full documentation](https://django-tenant-options.readthedocs.io/en/latest/) for more details and start empowering your tenants today!
