"""Admin classes for the Django Tenant Options package."""

import logging

from django.contrib import admin


logger = logging.getLogger("django_tenant_options")


class BaseOptionsAdminMixin:
    """Mixin providing functionality specific to Options models"""

    search_fields = []
    list_display = []


class BaseOptionsAdmin(BaseOptionsAdminMixin, admin.ModelAdmin):
    pass


class SelectionsAdminMixin:
    search_fields = []
    list_display = []


class BaseSelectionsAdmin(SelectionsAdminMixin, admin.ModelAdmin):
    pass
