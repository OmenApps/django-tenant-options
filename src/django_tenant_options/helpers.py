"""Helper functions for the django_tenant_options app."""

from django_tenant_options.models import AbstractOption
from django_tenant_options.models import AbstractSelection


def all_option_subclasses():
    """Returns a list of model classes that subclass AbstractOption."""
    return AbstractOption.get_concrete_subclasses()


def all_selection_subclasses():
    """Returns a list of model classes that subclass AbstractSelection."""
    return AbstractSelection.get_concrete_subclasses()


def get_default_option_names(option_model):
    """Return the sorted list of default option names for a concrete Option model.

    Reads the ``default_options`` class dict on the given model and returns its keys
    sorted alphabetically. Returns an empty list when the model defines no defaults.
    """
    default_options = getattr(option_model, "default_options", {}) or {}
    return sorted(default_options.keys())
