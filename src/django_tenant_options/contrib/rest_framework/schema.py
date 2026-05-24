"""drf-spectacular schema helpers, soft-guarded so they degrade to no-ops.

``drf-spectacular`` is optional. Install it via
``pip install django-tenant-options[spectacular]``.

``maybe_extend_schema`` applies ``drf_spectacular.utils.extend_schema`` when the
library is installed, and returns an identity decorator otherwise, so views can
be decorated without taking a hard dependency on drf-spectacular.
"""

try:
    from drf_spectacular.utils import OpenApiExample
    from drf_spectacular.utils import extend_schema

    SPECTACULAR_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when spectacular is absent
    OpenApiExample = None
    extend_schema = None
    SPECTACULAR_AVAILABLE = False


def _identity(func):
    """Return the function unchanged (no-op decorator)."""
    return func


def maybe_extend_schema(**kwargs):
    """Return ``extend_schema(**kwargs)`` when available, else a no-op decorator.

    Usage on a view or action::

        @maybe_extend_schema(summary="List available options")
        def list(self, request, *args, **kwargs):
            ...
    """
    if SPECTACULAR_AVAILABLE:
        return extend_schema(**kwargs)
    return _identity


def option_list_example():
    """Return an OpenApiExample for a list of options, or None if unavailable."""
    if not SPECTACULAR_AVAILABLE:
        return None
    return OpenApiExample(
        "Available options",
        value=[
            {"id": 1, "name": "High", "option_type": "dm", "deleted": None, "tenant": None},
            {"id": 2, "name": "Custom", "option_type": "cu", "deleted": None, "tenant": 7},
        ],
        response_only=True,
    )
