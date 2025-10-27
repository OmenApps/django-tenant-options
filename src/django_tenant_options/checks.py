"""Checks for the django_tenant_options app."""

import inspect

from django.conf import settings
from django.core.checks import Error
from django.core.checks import Warning


def check_manager_compliance(
    model,
    manager,
    required_manager,
    required_queryset,
    error_ids,
):
    """Helper function to check if a manager complies with requirements."""
    results = []

    if not settings.DEBUG:
        # Skip this check in production
        return results

    # Check if the manager is a subclass of the required manager
    manager_mro = inspect.getmro(manager.__class__)
    queryset_mro = inspect.getmro(manager._queryset_class)

    if required_manager not in manager_mro:
        results.append(
            Warning(
                f"Model manager '{manager.__class__.__name__}' does not inherit from '{required_manager.__name__}', "
                "so filtering may not work as expected.",
                obj=model,
                id=f"django_tenant_options.I{error_ids[0]}",
            )
        )
    elif required_queryset not in queryset_mro:
        results.append(
            Error(
                f"Manager {manager.__class__.__name__} must use a queryset that inherits from "
                f"{required_queryset.__name__}",
                obj=model,
                id=f"django_tenant_options.E{error_ids[1]}",
            )
        )
    return results
