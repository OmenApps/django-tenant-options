# Tutorial: Build a Task Manager with Tenant-Specific Options

In this tutorial, you'll build a task management application where different tenants (organizations) can customize their task priorities and statuses. By the end, you'll have a working application where:

- Developers define mandatory and optional default priorities and statuses
- Tenant admins choose which optional defaults to enable and create custom options
- End users see only the options their tenant has selected

The [example project](https://github.com/OmenApps/django-tenant-options/tree/main/example_project) in the repository contains the complete working version of what you'll build here. Reference it if you get stuck.

```{note}
This tutorial uses plain Django (no auto_prefetch, no crispy-forms) to keep dependencies minimal. See [Customization](customization.md) for integrating those packages.
```

## What you'll build

A multi-tenant task manager with:

- **Tenant** and **User** models
- **Task Priority** options (Critical, High, Medium, Low) with customization per tenant
- **Task Status** options (New, In Progress, Completed, Archived) with customization per tenant
- **Task** model with ForeignKey fields to both option types
- Forms for creating tasks, managing options, and managing selections
- Views and templates that respect tenant boundaries

![Screenshot of task priorities](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Task-Priority-Options.png)

## Prerequisites

- Python 3.11+
- Basic familiarity with Django models, forms, and views
- A fresh Django project (or an existing one you want to add options to)

## Step 1: Install and configure

Install the package:

```bash
pip install django-tenant-options
```

Add it to `INSTALLED_APPS` in your `settings.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_tenant_options",
    "tasks",  # your app
]
```

## Step 2: Create your Tenant and User models

In `tasks/models.py`, start with a basic tenant model and a User model with a tenant ForeignKey:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class Tenant(models.Model):
    """Represents an organization in the SaaS application."""

    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom user with a tenant association."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
```

Point your `AUTH_USER_MODEL` setting at this custom user:

```python
# settings.py
AUTH_USER_MODEL = "tasks.User"
```

And configure the tenant model for `django-tenant-options`:

```python
# settings.py
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "tasks.Tenant",
}
```

## Step 3: Define Task Priority models

Now create the Option and Selection models for task priorities. Each set of customizable options uses a pair of models -- an Option model that stores all available choices, and a Selection model that tracks which options each tenant has enabled.

Add to `tasks/models.py`:

```python
from django_tenant_options.models import AbstractOption, AbstractSelection
from django_tenant_options.choices import OptionType


class TaskPriorityOption(AbstractOption):
    """Available task priority options."""

    tenant_model = "tasks.Tenant"
    selection_model = "tasks.TaskPrioritySelection"

    default_options = {
        "Critical": {"option_type": OptionType.OPTIONAL},
        "High": {"option_type": OptionType.MANDATORY},
        "Medium": {"option_type": OptionType.OPTIONAL},
        "Low": {},  # Empty dict defaults to MANDATORY
    }

    class Meta(AbstractOption.Meta):
        verbose_name = "Task Priority Option"
        verbose_name_plural = "Task Priority Options"


class TaskPrioritySelection(AbstractSelection):
    """Tracks which priority options each tenant has enabled."""

    tenant_model = "tasks.Tenant"
    option_model = "tasks.TaskPriorityOption"

    class Meta(AbstractSelection.Meta):
        verbose_name = "Task Priority Selection"
        verbose_name_plural = "Task Priority Selections"
```

Key points:

- `"High"` and `"Low"` are **mandatory** -- every tenant's users will see them.
- `"Critical"` and `"Medium"` are **optional** -- each tenant chooses whether to enable them.
- Tenants can also create **custom** priorities (e.g., "Urgent", "Blocked").
- The `Meta` class inherits from `AbstractOption.Meta` / `AbstractSelection.Meta` to preserve database constraints.

## Step 4: Define Task Status models

Repeat the pattern for task statuses. Add to `tasks/models.py`:

```python
class TaskStatusOption(AbstractOption):
    """Available task status options."""

    tenant_model = "tasks.Tenant"
    selection_model = "tasks.TaskStatusSelection"

    default_options = {
        "New": {"option_type": OptionType.MANDATORY},
        "In Progress": {"option_type": OptionType.OPTIONAL},
        "Completed": {"option_type": OptionType.MANDATORY},
        "Archived": {"option_type": OptionType.MANDATORY},
    }

    class Meta(AbstractOption.Meta):
        verbose_name = "Task Status Option"
        verbose_name_plural = "Task Status Options"


class TaskStatusSelection(AbstractSelection):
    """Tracks which status options each tenant has enabled."""

    tenant_model = "tasks.Tenant"
    option_model = "tasks.TaskStatusOption"

    class Meta(AbstractSelection.Meta):
        verbose_name = "Task Status Selection"
        verbose_name_plural = "Task Status Selections"
```

You now have two independent sets of customizable options. The same pattern works for any kind of option your tenants might need.

## Step 5: Create the Task model

Add the `Task` model with ForeignKey fields to both option types:

```python
class Task(models.Model):
    """A task assigned to a user with customizable priority and status."""

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    user = models.ForeignKey(
        "tasks.User",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    priority = models.ForeignKey(
        "tasks.TaskPriorityOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    status = models.ForeignKey(
        "tasks.TaskStatusOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    def __str__(self):
        return self.title
```

```{tip}
Using `on_delete=models.SET_NULL` with `null=True` means that if an option is ever hard-deleted, tasks won't be deleted along with it.
```

## Step 6: Run migrations and sync options

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py syncoptions
```

The `syncoptions` command creates the default option records in your database. Verify with:

```bash
python manage.py listoptions
```

You should see the priority and status options listed with their types.

## Step 7: Create forms

Create `tasks/forms.py`:

```python
from django import forms
from django_tenant_options.forms import (
    OptionCreateFormMixin,
    OptionUpdateFormMixin,
    SelectionsForm,
    UserFacingFormMixin,
)
from .models import (
    Task,
    TaskPriorityOption,
    TaskPrioritySelection,
    TaskStatusOption,
    TaskStatusSelection,
)


# End-user form for creating/editing tasks
class TaskForm(UserFacingFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "priority", "status"]


# Forms for tenant admins to create custom options
class TaskPriorityCreateForm(OptionCreateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = ["name", "option_type", "tenant", "deleted"]


class TaskStatusCreateForm(OptionCreateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskStatusOption
        fields = ["name", "option_type", "tenant", "deleted"]


# Forms for tenant admins to update/delete custom options
class TaskPriorityUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = "__all__"


class TaskStatusUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskStatusOption
        fields = "__all__"


# Forms for tenant admins to manage which options are enabled
class TaskPrioritySelectionForm(SelectionsForm):
    class Meta:
        model = TaskPrioritySelection


class TaskStatusSelectionForm(SelectionsForm):
    class Meta:
        model = TaskStatusSelection
```

The form types and when to use them:

| Form | Mixin | Used by | Purpose |
|------|-------|---------|---------|
| `TaskForm` | `UserFacingFormMixin` | End users | Create/edit tasks with filtered option choices |
| `TaskPriorityCreateForm` | `OptionCreateFormMixin` | Tenant admins | Create new custom priority options |
| `TaskPriorityUpdateForm` | `OptionUpdateFormMixin` | Tenant admins | Update or soft-delete custom options |
| `TaskPrioritySelectionForm` | `SelectionsForm` | Tenant admins | Enable/disable optional priorities |

## Step 8: Build views

Create `tasks/views.py`. Every form that uses a `django-tenant-options` mixin must receive a `tenant` argument:

```python
from django.shortcuts import get_object_or_404, redirect, render
from .forms import (
    TaskForm,
    TaskPriorityCreateForm,
    TaskPrioritySelectionForm,
    TaskStatusCreateForm,
    TaskStatusSelectionForm,
)
from .models import (
    Task,
    TaskPriorityOption,
    TaskPrioritySelection,
    TaskStatusOption,
    TaskStatusSelection,
)


def task_list(request):
    tasks = Task.objects.filter(user=request.user)
    return render(request, "tasks/task_list.html", {"tasks": tasks})


def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect("task_list")
    else:
        form = TaskForm(tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form, "title": "Create Task"})


def task_update(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("task_list")
    else:
        form = TaskForm(instance=task, tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form, "title": "Edit Task"})


def priority_list(request):
    options = TaskPriorityOption.objects.options_for_tenant(request.user.tenant)
    selections = TaskPrioritySelection.objects.selected_options_for_tenant(
        tenant=request.user.tenant
    )
    return render(request, "tasks/option_list.html", {
        "options": options,
        "selections": selections,
        "title": "Task Priorities",
        "create_url": "priority_create",
        "selections_url": "priority_selections",
    })


def priority_create(request):
    if request.method == "POST":
        form = TaskPriorityCreateForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("priority_list")
    else:
        form = TaskPriorityCreateForm(tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form, "title": "Create Priority"})


def priority_selections(request):
    if request.method == "POST":
        form = TaskPrioritySelectionForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("priority_list")
    else:
        form = TaskPrioritySelectionForm(tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form, "title": "Manage Priority Selections"})
```

The pattern is the same for status options -- create analogous views for `status_list`, `status_create`, and `status_selections`.

## Step 9: Create templates

Create a base template and a few page templates.

**`tasks/templates/tasks/form.html`:**

```html
<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body>
  <h1>{{ title }}</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Save</button>
  </form>
</body>
</html>
```

**`tasks/templates/tasks/task_list.html`:**

```html
<!DOCTYPE html>
<html>
<head><title>Tasks</title></head>
<body>
  <h1>Tasks</h1>
  <a href="{% url 'task_create' %}">Create Task</a>
  <table>
    <tr><th>Title</th><th>Priority</th><th>Status</th><th></th></tr>
    {% for task in tasks %}
    <tr>
      <td>{{ task.title }}</td>
      <td>{{ task.priority }}</td>
      <td>{{ task.status }}</td>
      <td><a href="{% url 'task_update' task.id %}">Edit</a></td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
```

**`tasks/templates/tasks/option_list.html`:**

```html
<!DOCTYPE html>
<html>
<head><title>{{ title }}</title></head>
<body>
  <h1>{{ title }}</h1>
  <p>
    <a href="{% url create_url %}">Create Custom Option</a> |
    <a href="{% url selections_url %}">Manage Selections</a>
  </p>

  <h2>Available Options</h2>
  <ul>
    {% for option in options %}
    <li>
      {{ option.name }}
      {% if option.option_type == "dm" %}
        <span style="color: green;">(Mandatory)</span>
      {% elif option.option_type == "do" %}
        <span style="color: blue;">(Optional)</span>
      {% else %}
        <span style="color: orange;">(Custom)</span>
      {% endif %}
    </li>
    {% endfor %}
  </ul>

  <h2>Currently Selected</h2>
  <ul>
    {% for selection in selections %}
    <li>{{ selection.name }}</li>
    {% endfor %}
  </ul>
</body>
</html>
```

## Step 10: Wire up URLs

Create `tasks/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path("", views.task_list, name="task_list"),
    path("create/", views.task_create, name="task_create"),
    path("<int:task_id>/edit/", views.task_update, name="task_update"),
    path("priorities/", views.priority_list, name="priority_list"),
    path("priorities/create/", views.priority_create, name="priority_create"),
    path("priorities/selections/", views.priority_selections, name="priority_selections"),
]
```

Include in your root `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tasks/", include("tasks.urls")),
]
```

## Step 11: Test it out

1. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

2. Start the server:
   ```bash
   python manage.py runserver
   ```

3. Log in via the admin at `http://127.0.0.1:8000/admin/`

4. Create a Tenant and assign your superuser to it (via the admin)

5. Visit `http://127.0.0.1:8000/tasks/priorities/` -- you should see the default priorities

6. Try managing selections -- enable/disable optional priorities

7. Create a custom priority option

8. Create a task -- the priority dropdown should show only the options your tenant has selected

![Screenshot of task creation form](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Task-Create-Form.png)

## Step 12: Validate your configuration

Run the validation command to confirm everything is properly set up:

```bash
python manage.py validate_tenant_options
```

You should see "All validations passed!" If there are warnings about missing constraints, check that your Meta classes inherit from the abstract model's Meta.

## What you've built

You now have a working multi-tenant task manager where:

- **Mandatory** options ("High", "Low", "New", "Completed", "Archived") are always available to every tenant
- **Optional** options ("Critical", "Medium", "In Progress") can be enabled or disabled per tenant
- Tenants can create **custom** options visible only to their users
- The `UserFacingFormMixin` automatically filters form choices to respect tenant selections
- Soft deletes preserve data integrity -- deleted options don't break existing records

## Next steps

- [Models Guide](models.md) -- Custom managers, querysets, and advanced model configuration
- [Forms Guide](forms.md) -- Deep dive into every form mixin
- [Views and Templates](views-and-templates.md) -- Class-based views, admin integration, template patterns
- [Commands](commands.md) -- Database triggers for extra integrity protection
- [Configuration Reference](configuration.md) -- Every available setting
- [Options Cookbook](optionscookbook.md) -- Inspiration for option sets across industries
