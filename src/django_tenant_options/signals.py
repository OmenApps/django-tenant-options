"""Cache-invalidation signals for django-tenant-options.

Connects post_save/post_delete receivers on every concrete Option and Selection subclass. Each
receiver bumps the namespace version for the relevant Option model label, invalidating all cached
per-tenant option lists for that model. Receivers early-return when caching is disabled, so they
are cheap no-ops in the default configuration.
"""

import logging

from django.apps import apps
from django.db.models.signals import post_delete
from django.db.models.signals import post_save

from django_tenant_options.cache import caching_enabled
from django_tenant_options.cache import safe_bump_version
from django_tenant_options.helpers import all_option_subclasses
from django_tenant_options.helpers import all_selection_subclasses


logger = logging.getLogger("django_tenant_options")


def _option_changed(sender, instance, **kwargs):
    """post_save/post_delete receiver for Option models: bump the option model's version."""
    if not caching_enabled():
        return
    label = type(instance)._meta.label
    safe_bump_version(label)


def _selection_changed(sender, instance, **kwargs):
    """post_save/post_delete receiver for Selection models: bump the related Option model's version."""
    if not caching_enabled():
        return
    try:
        option_model_str = type(instance).option_model
        option_label = apps.get_model(option_model_str)._meta.label
    except (LookupError, AttributeError):
        logger.warning("Could not resolve option_model for selection %r; skipping cache bump", instance)
        return
    safe_bump_version(option_label)


def connect_cache_signals() -> None:
    """Connect post_save/post_delete cache-invalidation receivers for all concrete subclasses.

    Safe to call multiple times: dispatch_uid ensures each receiver is connected only once per
    sender.
    """
    for option_model in all_option_subclasses():
        post_save.connect(
            _option_changed,
            sender=option_model,
            dispatch_uid=f"dto_option_save_{option_model._meta.label}",
        )
        post_delete.connect(
            _option_changed,
            sender=option_model,
            dispatch_uid=f"dto_option_delete_{option_model._meta.label}",
        )

    for selection_model in all_selection_subclasses():
        post_save.connect(
            _selection_changed,
            sender=selection_model,
            dispatch_uid=f"dto_selection_save_{selection_model._meta.label}",
        )
        post_delete.connect(
            _selection_changed,
            sender=selection_model,
            dispatch_uid=f"dto_selection_delete_{selection_model._meta.label}",
        )
