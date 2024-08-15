"""Admin classes for the users app."""

from django.apps import apps
from django.contrib import admin

from example_project.example.models import Task
from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import TaskStatusOption
from example_project.example.models import TaskStatusSelection
from example_project.example.models import Tenant


class TaskAdmin(admin.ModelAdmin):
    """Admin class for the Task model."""

    list_display = ("title", "description", "status", "priority")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["priority"].queryset = TaskPrioritySelection.objects.selected_options_for_tenant(
            tenant=request.user.tenant
        )
        form.base_fields["status"].queryset = TaskStatusSelection.objects.selected_options_for_tenant(
            tenant=request.user.tenant
        )
        return form


admin.site.register(Task, TaskAdmin)


class ListAdminMixin:
    """Mixin to automatically set list_display to all fields on a model."""

    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        super().__init__(model, admin_site)


# Register all models from the example app with the ListAdminMixin
for model in apps.get_app_config("example").get_models():
    AdminClass = type("AdminClass", (ListAdminMixin, admin.ModelAdmin), {})
    try:
        admin.site.register(model, AdminClass)
    except admin.sites.AlreadyRegistered:
        pass
