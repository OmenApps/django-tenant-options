"""ViewSets for exposing tenant options over Django REST Framework.

Requires ``djangorestframework``. Install via ``pip install django-tenant-options[drf]``.

These viewsets are model-agnostic. Subclass them, bind your concrete model and
serializer, and override ``get_tenant`` to resolve the tenant from the request.
The package never assumes how a tenant is derived from a request.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response


class BaseOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset over a concrete AbstractOption subclass.

    Subclasses must set ``option_model`` and ``serializer_class`` and override
    ``get_tenant``. Read-only by default for safety - options are managed via
    the package's forms/commands, while the API exposes them for selection UIs.
    """

    option_model = None
    serializer_class = None

    def get_tenant(self):
        """Return the tenant for the current request.

        Override this to resolve the tenant from ``self.request`` however your
        application identifies tenants (subdomain, header, user attribute, ...).
        """
        raise NotImplementedError(
            "Subclasses of BaseOptionViewSet must override get_tenant() to resolve the tenant from self.request."
        )

    def get_queryset(self):
        """Return all options available to the current tenant."""
        return self.option_model.objects.options_for_tenant(self.get_tenant())

    @action(detail=False)
    def selected(self, request, *args, **kwargs):
        """Return only the options actively selected by the current tenant."""
        queryset = self.option_model.objects.selected_options_for_tenant(self.get_tenant())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class BaseSelectionViewSet(viewsets.ModelViewSet):
    """Read/write viewset over a concrete AbstractSelection subclass.

    Subclasses must set ``selection_model`` and ``serializer_class`` and override
    ``get_tenant``. Listing returns the tenant's active selections. Creating sets
    the tenant automatically. Deleting performs a soft-delete.
    """

    selection_model = None
    serializer_class = None

    def get_tenant(self):
        """Return the tenant for the current request.

        Override this to resolve the tenant from ``self.request``.
        """
        raise NotImplementedError(
            "Subclasses of BaseSelectionViewSet must override get_tenant() to resolve the tenant from self.request."
        )

    def get_queryset(self):
        """Return the current tenant's active (non-deleted) selections."""
        return self.selection_model.objects.filter(
            tenant=self.get_tenant(),
            deleted__isnull=True,
        )

    def perform_create(self, serializer):
        """Save the selection with the tenant forced to the current tenant.

        The model's ``clean()`` raises Django's ``ValidationError`` for invalid
        selections (for example selecting another tenant's custom option). Translate
        it into a DRF ``ValidationError`` so the API returns 400 rather than 500.
        """
        try:
            serializer.save(tenant=self.get_tenant())
        except DjangoValidationError as exc:
            raise DRFValidationError(getattr(exc, "messages", [str(exc)])) from exc

    def perform_destroy(self, instance):
        """Soft-delete the selection instead of removing the row."""
        instance.delete()
