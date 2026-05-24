"""Router helpers for wiring tenant-option viewsets into URLconf.

Requires ``djangorestframework``. Install via ``pip install django-tenant-options[drf]``.

Example wiring in your project's urls.py::

    from django.urls import include
    from django.urls import path

    from django_tenant_options.contrib.rest_framework.routers import build_router

    from myapp.api import PriorityOptionViewSet

    router = build_router("priorities", PriorityOptionViewSet)

    urlpatterns = [
        path("api/", include(router.urls)),
    ]
"""

from rest_framework.routers import DefaultRouter


def build_router(prefix, viewset, basename=None):
    """Build a DefaultRouter with a single viewset registered.

    Args:
        prefix: URL prefix for the viewset (for example ``"priorities"``).
        viewset: A ViewSet class (typically a BaseOptionViewSet subclass).
        basename: Optional basename. Defaults to the prefix.

    Returns:
        A ``DefaultRouter`` instance with the viewset registered.
    """
    router = DefaultRouter()
    router.register(prefix, viewset, basename=basename or prefix)
    return router
