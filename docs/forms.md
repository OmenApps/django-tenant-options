# Forms

`django-tenant-options` provides form mixins and fields that handle tenant-aware option filtering. This guide covers each one in detail.

Every form mixin in this package requires a `tenant` argument passed from your view. Forgetting this raises `NoTenantProvidedFromViewError`.

## UserFacingFormMixin

Use this mixin for forms that end users interact with -- task creation forms, order forms, any form where a user selects from available options.

```python
from django import forms
from django_tenant_options.forms import UserFacingFormMixin


class TaskForm(UserFacingFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "priority", "status"]
```

### What it does automatically

When initialized with a `tenant`, the mixin:

1. **Finds ForeignKey fields** pointing to any `AbstractOption` subclass
2. **Filters their querysets** to show only options the tenant has selected (via `selected_options_for_tenant()`)
3. **Hides the tenant field** if present (sets it to `HiddenInput`)
4. **Removes the `associated_tenants` field** if present
5. **Handles deleted selections** -- if an existing record references a deleted option, the behavior depends on the `DISABLE_FIELD_FOR_DELETED_SELECTION` setting

### Deleted selection behavior

When a tenant deselects an option but existing records still reference it:

- **`DISABLE_FIELD_FOR_DELETED_SELECTION = False`** (default): The user must select a new option when editing the record. The deleted option won't appear as a choice.
- **`DISABLE_FIELD_FOR_DELETED_SELECTION = True`**: The deleted option appears in the dropdown but is disabled (read-only). The user sees what was previously selected but can't change it.

In both cases, deleted options never appear in forms for *new* records.

### View integration

Pass `tenant` from your view:

```python
# Function-based view
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("task_list")
    else:
        form = TaskForm(tenant=request.user.tenant)
    return render(request, "tasks/form.html", {"form": form})

# Class-based view
class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs
```

## OptionCreateFormMixin

Use this mixin for forms that let tenant admins create new custom options.

```python
from django import forms
from django_tenant_options.forms import OptionCreateFormMixin


class TaskPriorityCreateForm(OptionCreateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = ["name", "option_type", "tenant", "deleted"]
```

### What it does automatically

1. **Validates the tenant** and hides the tenant field (`HiddenInput`)
2. **Sets `option_type` to `OptionType.CUSTOM`** and hides it -- tenant-created options are always custom
3. **Hides the `deleted` field** and initializes it to `None`
4. **Removes `associated_tenants`** if present
5. **Enforces `option_type = CUSTOM` in `clean()`** -- even if someone manipulates the hidden field

### Specifying fields

You can use `fields = "__all__"` or list specific fields. Either way, the mixin will hide fields that tenants shouldn't see (tenant, option_type, deleted):

```python
# Explicit fields -- recommended for clarity
class TaskPriorityCreateForm(OptionCreateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = ["name", "option_type", "tenant", "deleted"]

# Implicit -- the mixin hides what it needs to
class TaskPriorityCreateForm(OptionCreateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = "__all__"
```

## OptionUpdateFormMixin

Extends `OptionCreateFormMixin` with a `delete` checkbox for soft-deleting options.

```python
from django import forms
from django_tenant_options.forms import OptionUpdateFormMixin


class TaskPriorityUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = "__all__"
```

### What it adds

On top of everything `OptionCreateFormMixin` does:

1. **Adds a `delete` BooleanField** (not required, defaults to False)
2. **In `clean()`**, if `delete` is checked, sets `cleaned_data["deleted"]` to the current timestamp

The resulting form lets tenant admins rename a custom option or soft-delete it in a single form.

### View integration

```python
def priority_update(request, option_id):
    option = get_object_or_404(TaskPriorityOption, id=option_id)
    if request.method == "POST":
        form = TaskPriorityUpdateForm(
            request.POST,
            instance=option,
            tenant=request.user.tenant,
        )
        if form.is_valid():
            form.save()
            return redirect("priority_list")
    else:
        form = TaskPriorityUpdateForm(
            instance=option,
            tenant=request.user.tenant,
        )
    return render(request, "priorities/form.html", {"form": form})
```

## SelectionsForm

Use this form to let tenant admins manage which options are enabled for their tenant.

```python
from django_tenant_options.forms import SelectionsForm


class TaskPrioritySelectionForm(SelectionsForm):
    class Meta:
        model = TaskPrioritySelection
```

### What it does

1. **Creates a `selections` field** -- a `ModelMultipleChoiceField` showing all options available to the tenant
2. **Pre-selects currently enabled options** as initial values
3. **In `clean()`**, automatically includes all mandatory options (even if the tenant tries to deselect them)
4. **Identifies removed selections** -- options that were previously selected but aren't in the new submission
5. **In `save()`**, uses an atomic transaction to:
   - Soft-delete removed selections (sets `deleted` timestamp)
   - Create or restore selections for newly chosen options

### Customizing the widget

You can adjust the selection widget in your form's `__init__`:

```python
class TaskPrioritySelectionForm(SelectionsForm):
    class Meta:
        model = TaskPrioritySelection

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["selections"].widget.attrs["size"] = "10"
```

### View integration

```python
def priority_selections(request):
    if request.method == "POST":
        form = TaskPrioritySelectionForm(
            request.POST,
            tenant=request.user.tenant,
        )
        if form.is_valid():
            form.save()
            return redirect("priority_list")
    else:
        form = TaskPrioritySelectionForm(tenant=request.user.tenant)
    return render(request, "priorities/selections.html", {"form": form})
```

## TenantFormBaseMixin

This is the base mixin that `OptionCreateFormMixin` and `SelectionsForm` build on. You generally don't use it directly, but it's useful to understand what it provides:

- Pops `tenant` from kwargs and validates it's not `None`
- Hides the `tenant` field if present
- Sets `option_type` to `CUSTOM` if the field exists
- Removes `associated_tenants` if present
- Overrides `clean()` to ensure `tenant` is always correct in cleaned data

## OptionsModelMultipleChoiceField

A custom `ModelMultipleChoiceField` used by `SelectionsForm` that displays option type labels alongside option names.

The default `label_from_instance` shows: `"Option Name (Mandatory)"`, `"Option Name (Optional)"`, or `"Option Name (Custom)"`.

### Custom display

To customize how options appear in the selection widget, subclass the field:

```python
from django_tenant_options.form_fields import OptionsModelMultipleChoiceField


class CustomOptionsField(OptionsModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} - {obj.get_option_type_display()}"
```

Then configure it globally:

```python
DJANGO_TENANT_OPTIONS = {
    "DEFAULT_MULTIPLE_CHOICE_FIELD": "yourapp.forms.CustomOptionsField",
}
```

## Common mistakes

### Forgetting to pass `tenant`

Every form that uses these mixins requires `tenant=` in its constructor call:

```python
# This will raise NoTenantProvidedFromViewError
form = TaskForm(request.POST)

# Correct
form = TaskForm(request.POST, tenant=request.user.tenant)
```

### Using the wrong mixin

- **End-user forms** (selecting an option for a record): `UserFacingFormMixin`
- **Creating custom options** (tenant admin): `OptionCreateFormMixin`
- **Updating/deleting custom options** (tenant admin): `OptionUpdateFormMixin`
- **Managing which options are enabled** (tenant admin): `SelectionsForm`

### Combining with crispy-forms

The mixins work with django-crispy-forms. Initialize the crispy helper after calling `super().__init__()`:

```python
class TaskPriorityCreateForm(OptionCreateFormMixin, ModelForm):
    class Meta:
        model = TaskPriorityOption
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset("Create Priority", *self.fields.keys()),
            Submit("submit", "Save"),
        )
```

## Further reading

- [Views and Templates](views-and-templates.md) -- Wiring forms into views and templates
- [Models Guide](models.md) -- The models behind the forms
- [Configuration Reference](configuration.md) -- Form-related settings
