"""Models for the example app."""
import auto_prefetch
from django.contrib.auth import get_user_model
from django.db import models

from django_tenant_options.choices import OptionType
from django_tenant_options.models import AbstractOption
from django_tenant_options.models import AbstractSelection


User = get_user_model()


class Tenant(auto_prefetch.Model):
    """A very simplistic example of how one might implement a Tenant architecture."""

    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True)

    def __str__(self):
        """Return the name of the Tenant."""
        return self.name

    class Meta(auto_prefetch.Model.Meta):
        """Meta class for Tenant."""

        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"


class Task(auto_prefetch.Model):
    """A very simplistic example of a Task model."""

    title = models.CharField(max_length=100)
    description = models.TextField()
    user = auto_prefetch.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    priority = auto_prefetch.ForeignKey(
        "example.TaskPriorityOption",
        on_delete=models.CASCADE,
        # null=True,
        # blank=True,
        related_name="tasks",
    )
    status = auto_prefetch.ForeignKey(
        "example.TaskStatusOption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    def __str__(self):
        """Return the title of the Task."""
        return self.title

    class Meta(auto_prefetch.Model.Meta):
        """Meta class for Task."""

        verbose_name = "Task"
        verbose_name_plural = "Tasks"


class TaskPriorityOption(AbstractOption):
    """Concrete implementation of AbstractOption for TaskPriority."""

    # Relying on the default tenant_model in project settings
    selection_model = "example.TaskPrioritySelection"
    default_options = {
        "Critical": {"option_type": OptionType.OPTIONAL},
        "High": {"option_type": OptionType.MANDATORY},
        "Medium": {"option_type": OptionType.OPTIONAL},
        "Low": {"option_type": OptionType.MANDATORY},
    }

    class Meta(AbstractOption.Meta, auto_prefetch.Model.Meta):
        """Meta class for TaskPriorityOption."""

        verbose_name = "Task Priority Option"
        verbose_name_plural = "Task Priority Options"


class TaskPrioritySelection(AbstractSelection):
    """Concrete implementation of AbstractSelection for TaskPriority."""

    tenant_model = "example.Tenant"  # Specifying the tenant_model here for demonstration purposes
    option_model = "example.TaskPriorityOption"

    class Meta(AbstractSelection.Meta, auto_prefetch.Model.Meta):
        """Meta class for TaskPrioritySelection."""

        verbose_name = "Task Priority Selection"
        verbose_name_plural = "Task Priority Selections"


class TaskStatusOption(AbstractOption):
    """Concrete implementation of AbstractOption for TaskStatus."""

    tenant_model = "example.Tenant"  # Specifying the tenant_model here for demonstration purposes
    selection_model = "example.TaskStatusSelection"
    default_options = {
        "New": {"option_type": OptionType.MANDATORY},
        "In Progress": {"option_type": OptionType.OPTIONAL},
        "Completed": {"option_type": OptionType.MANDATORY},
        "Archived": {"option_type": OptionType.MANDATORY},
    }

    class Meta(AbstractOption.Meta, auto_prefetch.Model.Meta):
        """Meta class for TaskStatusOption."""

        verbose_name = "Task Status Option"
        verbose_name_plural = "Task Status Options"


class TaskStatusSelection(AbstractSelection):
    """Concrete implementation of AbstractSelection for TaskStatus."""

    # Relying on the default tenant_model in project settings
    option_model = "example.TaskStatusOption"

    class Meta(AbstractSelection.Meta, auto_prefetch.Model.Meta):
        """Meta class for TaskStatusSelection."""

        verbose_name = "Task Status Selection"
        verbose_name_plural = "Task Status Selections"
