"""Helper functions for the django_tenant_options app."""

from django_tenant_options.models import AbstractOption
from django_tenant_options.models import AbstractSelection


def all_option_subclasses():
    """Returns a list of model classes that subclass AbstractOption."""
    return AbstractOption.get_concrete_subclasses()


def all_selection_subclasses():
    """Returns a list of model classes that subclass AbstractSelection."""
    return AbstractSelection.get_concrete_subclasses()
