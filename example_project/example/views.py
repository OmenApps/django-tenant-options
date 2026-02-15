"""Views for example app."""

import logging

from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.response import TemplateResponse

from .forms import TaskForm
from .forms import TaskPriorityOptionCreateForm
from .forms import TaskPrioritySelectionForm
from .forms import TaskStatusOptionCreateForm
from .forms import TaskStatusOptionUpdateForm
from .forms import TaskStatusSelectionForm
from .forms import TenantForm
from .models import Task
from .models import TaskPriorityOption
from .models import TaskPrioritySelection
from .models import TaskStatusOption
from .models import TaskStatusSelection
from .models import Tenant


logger = logging.getLogger("django_tenant_options")


def home(request):
    """Home view shows a list of urls to navigate the example app.

    In this view, we also set the current Tenant for the User if it is not already set, for example purposes only.
    """
    if not request.user.tenant:
        request.user.tenant = Tenant.objects.first()
        request.user.save()
    return render(request, "example/home.html")


def task_list(request):
    """Lists all Tasks for the current Tenant."""
    template = "example/task_list.html"
    context = {}

    tasks = Task.objects.filter(user=request.user)

    context["tasks"] = tasks

    return TemplateResponse(request, template, context)


def task_create(request):
    """Creates a Task for the current Tenant."""
    template = "example/form.html"
    context = {}

    if request.method == "POST":
        form = TaskForm(request.POST, tenant=request.user.tenant, request=request)
        if form.is_valid():
            form.save()
            return redirect("example:task_list")
    else:
        form = TaskForm(tenant=request.user.tenant, request=request)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_update(request, task_id):
    """Updates a Task for the current Tenant."""
    template = "example/form.html"
    context = {}

    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, tenant=request.user.tenant, request=request)
        if form.is_valid():
            form.save()
            return redirect("example:task_list")
    else:
        form = TaskForm(instance=task, tenant=request.user.tenant, request=request)

    context["form"] = form

    return TemplateResponse(request, template, context)


def user_tenant_update(request, tenant_id):
    """Updates a Tenant for the current User."""

    tenant = get_object_or_404(Tenant, id=tenant_id)
    request.user.tenant = tenant
    request.user.save()

    return redirect("example:tenant_list")


def tenant_list(request):
    """Lists all Tenants."""
    template = "example/tenant_list.html"
    context = {}

    tenants = Tenant.objects.all()

    context["tenants"] = tenants

    return TemplateResponse(request, template, context)


def tenant_create(request):
    """Creates a Tenant."""
    template = "example/form.html"
    context = {}

    if request.method == "POST":
        form = TenantForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("example:tenant_list")
    else:
        form = TenantForm()

    context["form"] = form

    return TemplateResponse(request, template, context)


def tenant_update(request, tenant_id):
    """Updates a Tenant."""
    template = "example/form.html"
    context = {}

    tenant = get_object_or_404(Tenant, id=tenant_id)

    if request.method == "POST":
        form = TenantForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            return redirect("example:tenant_list")
    else:
        form = TenantForm(instance=tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_priority_list(request):
    """Lists all TaskPriorityOption and TaskPrioritySelection for the current Tenant."""
    template = "example/task_priority_list.html"
    context = {}

    task_priority_options = TaskPriorityOption.objects.options_for_tenant(request.user.tenant)
    context["task_priority_options"] = task_priority_options

    task_priority_selections = TaskPrioritySelection.objects.selected_options_for_tenant(
        tenant=request.user.tenant
    ).filter(deleted__isnull=True)
    context["task_priority_selections"] = task_priority_selections

    return TemplateResponse(request, template, context)


def task_status_list(request):
    """Lists all TaskStatusOption and TaskStatusSelection for the current Tenant."""
    template = "example/task_status_list.html"
    context = {}

    task_status_options = TaskStatusOption.objects.options_for_tenant(request.user.tenant)
    context["task_status_options"] = task_status_options

    task_status_selections = TaskStatusSelection.objects.selected_options_for_tenant(tenant=request.user.tenant)
    context["task_status_selections"] = task_status_selections

    return TemplateResponse(request, template, context)


def task_priority_option_create(request):
    """Creates a TaskPriorityOption for the current Tenant."""
    template = "example/form.html"
    context = {}

    if request.method == "POST":
        form = TaskPriorityOptionCreateForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("example:task_priority_list")
    else:
        form = TaskPriorityOptionCreateForm(tenant=request.user.tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_priority_option_update(request, task_priority_option_id):
    """Updates a TaskPriorityOption for the current Tenant."""
    template = "example/form.html"
    context = {}

    task_priority_option = get_object_or_404(TaskPriorityOption, id=task_priority_option_id)
    logger.debug(f"Current tenant: {request.user.tenant}")

    if request.method == "POST":
        form = TaskStatusOptionUpdateForm(request.POST, instance=task_priority_option, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("example:task_priority_list")
    else:
        form = TaskStatusOptionUpdateForm(instance=task_priority_option, tenant=request.user.tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_status_option_create(request):
    """Creates a TaskStatusOption for the current Tenant."""
    template = "example/form.html"
    context = {}

    if request.method == "POST":
        form = TaskStatusOptionCreateForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("example:task_status_list")
    else:
        form = TaskStatusOptionCreateForm(tenant=request.user.tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_status_option_update(request, task_status_option_id):
    """Updates a TaskStatusOption for the current Tenant."""
    template = "example/form.html"
    context = {}

    task_status_option = get_object_or_404(TaskStatusOption, id=task_status_option_id)

    if request.method == "POST":
        form = TaskStatusOptionCreateForm(request.POST, instance=task_status_option, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("example:task_status_list")
    else:
        form = TaskStatusOptionCreateForm(instance=task_status_option, tenant=request.user.tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_priority_selections_update(request):
    """Creates a TaskPrioritySelection for the current Tenant."""
    template = "example/form.html"
    context = {}

    if request.method == "POST":
        form = TaskPrioritySelectionForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("example:task_priority_list")
    else:
        form = TaskPrioritySelectionForm(tenant=request.user.tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)


def task_status_selections_update(request):
    """Creates a TaskStatusSelection for the current Tenant."""
    template = "example/form.html"
    context = {}

    if request.method == "POST":
        form = TaskStatusSelectionForm(request.POST, tenant=request.user.tenant)
        if form.is_valid():
            form.save()
            return redirect("example:task_status_list")
    else:
        form = TaskStatusSelectionForm(tenant=request.user.tenant)

    context["form"] = form

    return TemplateResponse(request, template, context)
