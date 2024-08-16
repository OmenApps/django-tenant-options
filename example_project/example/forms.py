"""Forms for the example app."""

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import Fieldset
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django.contrib.auth import get_user_model
from django.forms import Form
from django.forms import ModelForm
from django.forms.widgets import HiddenInput

from django_tenant_options.forms import OptionCreateFormMixin
from django_tenant_options.forms import OptionUpdateFormMixin
from django_tenant_options.forms import SelectionsModelForm

from .models import Task
from .models import TaskPriorityOption
from .models import TaskPrioritySelection
from .models import TaskStatusOption
from .models import TaskStatusSelection
from .models import Tenant


User = get_user_model()


class TaskForm(UserFacingFormMixin, ModelForm):
    """Form for creating Task instances."""

    class Meta:
        """Meta class for TaskForm."""

        model = Task
        fields = "__all__"

    def __init__(self, *args, tenant=None, **kwargs):
        """Initialize TaskForm with a tenant."""
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["priority"].queryset = TaskPrioritySelection.objects.selected_options_for_tenant(tenant=tenant)
        self.fields["status"].queryset = TaskStatusSelection.objects.selected_options_for_tenant(tenant=tenant)

        self.data = self.data.copy()
        self.data.update(user=User.objects.filter(id=self.request.user.id).first().pk)
        self.fields["user"].widget = HiddenInput()

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Create or Update Task",
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )

    def save(self, commit=True):
        """Save the Task instance."""
        task = super().save(commit=False)
        task.user = User.objects.filter(id=self.request.user.id).first()
        if commit:
            task.save()
        return task


class TenantForm(ModelForm):
    """Form for creating Tenant instances."""

    class Meta:
        """Meta class for TenantForm."""

        model = Tenant
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Create or Update Tenant",
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class TaskStatusOptionCreateForm(OptionCreateFormMixin, ModelForm):
    """Form for creating TaskStatusOption instances."""

    class Meta:
        """Meta class for TaskStatusOptionCreateForm."""

        model = TaskStatusOption
        fields = ["name", "option_type", "tenant", "deleted"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Create or Update Task Status Option",
                HTML("<p>Note: Only custom Options can be created or updated here.</p>"),
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class TaskStatusOptionUpdateForm(OptionUpdateFormMixin, ModelForm):
    """Form for updating TaskStatusOption instances."""

    class Meta:
        """Meta class for TaskStatusOptionUpdateForm.

        If the delete field is checked, the TaskStatusOption `deleted` field will be set to the current datetime.
        """

        model = TaskStatusOption
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Create or Update Task Status Option",
                HTML("<p>Note: Only custom Options can be created or updated here.</p>"),
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class TaskPriorityOptionCreateForm(OptionCreateFormMixin, ModelForm):
    """Form for creating TaskPriorityOption instances."""

    class Meta:
        """Meta class for TaskPriorityOptionCreateForm."""

        model = TaskPriorityOption
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Create or Update Task Priority Option",
                HTML("<p>Note: Only custom Options can be created or updated here.</p>"),
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class TaskPriorityOptionUpdateForm(OptionUpdateFormMixin, ModelForm):
    """Form for updating TaskPriorityOption instances."""

    class Meta:
        """Meta class for TaskPriorityOptionUpdateForm.

        If the delete field is checked, the TaskPriorityOption `deleted` field will be set to the current datetime.
        """

        model = TaskPriorityOption
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Create or Update Task Priority Option",
                HTML("<p>Note: Only custom Options can be created or updated here.</p>"),
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class TaskStatusSelectionForm(SelectionsForm):
    """Form for creating TaskStatusSelection instances."""

    class Meta:
        """Meta class for TaskStatusSelectionForm."""

        model = TaskStatusSelection

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Example increasing widget size
        self.fields["selections"].widget.attrs["size"] = "10"

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Update Task Status Selections",
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class TaskPrioritySelectionForm(SelectionsModelForm):
    """Form for creating TaskPrioritySelection instances."""

    class Meta:
        """Meta class for TaskPrioritySelectionForm."""

        model = TaskPrioritySelection

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Update Task Priority Selections",
                *self.fields.keys(),
            ),
            Submit("submit", "Submit", css_class="button white"),
        )


class EndUserForm(Form):
    """Form for viewing a form from an end-user perspective."""
