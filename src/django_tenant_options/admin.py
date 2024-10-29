"""Admin classes for the Django Tenant Options package."""

import logging

from django.contrib import admin


logger = logging.getLogger("django_tenant_options")


class BaseOptionsAdminMixin:
    """Mixin providing functionality specific to Options models."""

    search_fields = []
    list_display = []


class BaseOptionsAdmin(BaseOptionsAdminMixin, admin.ModelAdmin):
    """Base class for Options Admin classes."""


class SelectionsAdminMixin:
    """Mixin providing functionality specific to Selections models."""

    search_fields = []
    list_display = []


class BaseSelectionsAdmin(SelectionsAdminMixin, admin.ModelAdmin):
    """Base class for Selections Admin classes."""
