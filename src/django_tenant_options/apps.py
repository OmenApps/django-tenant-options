"""App configuration for the Django Tenant Options package."""

from django.apps import AppConfig


class DjangoTenantOptionsConfig(AppConfig):
    """App configuration for the Django Tenant Options package."""

    name = "django_tenant_options"
    verbose_name = "Django Tenant Options"

    def ready(self):
        """Perform application initialization.

        Connect per-tenant option cache-invalidation signals. The receivers early-return when
        caching is disabled, so this is cheap regardless of the CACHE_OPTIONS setting.
        """
        from django_tenant_options.signals import connect_cache_signals

        connect_cache_signals()
