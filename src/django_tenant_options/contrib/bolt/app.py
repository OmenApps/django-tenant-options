"""Thin, guarded django-bolt adapter mirroring the DRF viewset behavior.

Exposes GET endpoints for a tenant's available and selected options on a
django-bolt app object. Kept intentionally small because django-bolt is
experimental. The package never assumes how a tenant is resolved from a
request, so callers pass a ``get_tenant(request)`` callable.
"""

try:
    import django_bolt  # noqa: F401

    BOLT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when django-bolt is absent
    BOLT_AVAILABLE = False


def _serialize_option(option):
    """Return a plain dict representation of an option for JSON responses."""
    return {
        "id": option.id,
        "name": option.name,
        "option_type": option.option_type,
        "deleted": option.deleted.isoformat() if option.deleted else None,
        "tenant": option.tenant_id,
    }


def register_option_routes(app, option_model, get_tenant, prefix="/options"):
    """Register available/selected GET routes on a django-bolt app.

    Args:
        app: A django-bolt app object exposing a ``get(path)`` decorator.
        option_model: A concrete AbstractOption subclass.
        get_tenant: Callable taking the request and returning the tenant.
        prefix: URL prefix for the registered routes.

    Returns:
        The app object, for chaining.
    """

    @app.get(f"{prefix}/available")
    def available_options(request):
        tenant = get_tenant(request)
        queryset = option_model.objects.options_for_tenant(tenant)
        return [_serialize_option(option) for option in queryset]

    @app.get(f"{prefix}/selected")
    def selected_options(request):
        tenant = get_tenant(request)
        queryset = option_model.objects.selected_options_for_tenant(tenant)
        return [_serialize_option(option) for option in queryset]

    return app
