"""App configuration for the Django Tenant Options package."""

from django.apps import AppConfig


class DjangoTenantOptionsConfig(AppConfig):
    """App configuration for the Django Tenant Options package."""

    name = "django_tenant_options"
    verbose_name = "Django Tenant Options"

    def ready(self):
        """Perform application initialization."""
