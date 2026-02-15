# Views and Templates

Patterns for passing tenants to forms, rendering options in templates, and registering models in the Django admin.

## Passing `tenant` to forms

Every form that uses a `django-tenant-options` mixin requires a `tenant` argument. How you determine the current tenant depends on your application architecture.

### Function-based views

```python
from django.shortcuts import get_object_or_404, redirect, render


def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("task_list")
    else:
        form = TaskForm(tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form})


def task_update(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("task_list")
    else:
        form = TaskForm(instance=task, tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form})
```

### Class-based views

Override `get_form_kwargs` to inject the tenant:

```python
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs
```

### Determining the current tenant

Your approach depends on your tenant architecture:

```python
# Direct ForeignKey on User
tenant = request.user.tenant

# Through a profile model
tenant = request.user.profile.organization

# From middleware that sets it on the request
tenant = request.tenant

# From the URL (e.g., subdomain-based)
tenant = Tenant.objects.get(subdomain=request.subdomain)
```

The package doesn't impose a particular tenant resolution strategy. As long as you pass a valid tenant model instance to the form, it works.

## Template patterns

### Displaying option types

Options have an `option_type` field with values `"dm"` (Mandatory), `"do"` (Optional), or `"cu"` (Custom). Use `get_option_type_display` for human-readable labels:

```html
<ul>
  {% for priority in priorities %}
  <li>
    {{ priority.name }}
    <span class="badge">{{ priority.get_option_type_display }}</span>
  </li>
  {% endfor %}
</ul>
```

### Color-coding by type

Apply CSS classes based on option type for visual distinction:

```html
{% for priority in priorities %}
<li>
  {{ priority.name }}
  {% if priority.option_type == "dm" %}
    <span class="badge badge-primary">Mandatory</span>
  {% elif priority.option_type == "do" %}
    <span class="badge badge-secondary">Optional</span>
  {% else %}
    <span class="badge badge-info">Custom</span>
  {% endif %}
</li>
{% endfor %}
```

### Listing options for a tenant

In your view, use the queryset methods to get the right set of options:

```python
def priority_list(request):
    # All options available to this tenant (mandatory + optional + custom)
    options = TaskPriorityOption.objects.options_for_tenant(request.user.tenant)

    # Only selected options (what users will see in forms)
    selections = TaskPrioritySelection.objects.selected_options_for_tenant(
        tenant=request.user.tenant
    )

    return render(request, "priorities/list.html", {
        "options": options,
        "selections": selections,
    })
```

### Simple form template

```html
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Save</button>
</form>
```

## Admin integration

The package provides base admin classes for registering Option and Selection models in the Django admin.

### Admin classes

```python
from django.contrib import admin
from django_tenant_options.admin import BaseOptionsAdmin, BaseSelectionsAdmin

from .models import TaskPriorityOption, TaskPrioritySelection


@admin.register(TaskPriorityOption)
class TaskPriorityOptionAdmin(BaseOptionsAdmin):
    list_display = ["name", "option_type", "tenant", "deleted"]
    list_filter = ["option_type", "deleted"]
    search_fields = ["name"]


@admin.register(TaskPrioritySelection)
class TaskPrioritySelectionAdmin(BaseSelectionsAdmin):
    list_display = ["option", "tenant", "deleted"]
    list_filter = ["deleted"]
```

### Admin mixins

If you need to combine with other admin base classes, use the mixins instead:

```python
from django_tenant_options.admin import BaseOptionsAdminMixin, SelectionsAdminMixin


class TaskPriorityOptionAdmin(BaseOptionsAdminMixin, SomeOtherAdminBase):
    # ...
    pass
```

### Tenant-aware admin forms

If you use a `UserFacingFormMixin` form in the admin, override `get_form` to pass the tenant:

```python
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    form = TaskForm

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class TenantForm(Form):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs["tenant"] = request.user.tenant
                super().__init__(*args, **inner_kwargs)

        return TenantForm
```

## URL patterns

A recommended URL structure for option management:

```python
from django.urls import path


urlpatterns = [
    # Tasks
    path("tasks/", views.task_list, name="task_list"),
    path("tasks/create/", views.task_create, name="task_create"),
    path("tasks/<int:task_id>/edit/", views.task_update, name="task_update"),

    # Priority options (tenant admin)
    path("priorities/", views.priority_list, name="priority_list"),
    path("priorities/create/", views.priority_create, name="priority_create"),
    path("priorities/<int:pk>/edit/", views.priority_update, name="priority_update"),
    path("priorities/selections/", views.priority_selections, name="priority_selections"),
]
```

## Further reading

- [Forms Guide](forms.md) -- Detailed coverage of each form mixin
- [Models Guide](models.md) -- Manager and queryset methods for views
- [Tutorial](tutorial.md) -- Building a complete application end to end
