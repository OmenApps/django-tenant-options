# REST Framework and API Integration

`django-tenant-options` ships optional, fully-guarded API integration extras.
The package core has no API dependencies - these extras live in
`django_tenant_options.contrib` and are imported only when you opt in.

## Installation

Install the extra that matches your stack:

```bash
# Django REST Framework only
pip install django-tenant-options[drf]

# DRF plus drf-spectacular OpenAPI schema
pip install django-tenant-options[spectacular]

# Experimental django-bolt adapter
pip install django-tenant-options[bolt]
```

Add `rest_framework` to your `INSTALLED_APPS` when using the DRF extra.

## Serializers

Serializers are model-agnostic. Subclass and bind your concrete Option model, or
use the factory:

```python
from django_tenant_options.contrib.rest_framework.serializers import option_serializer_factory

from myapp.models import TaskPriorityOption

PriorityOptionSerializer = option_serializer_factory(TaskPriorityOption)
```

Or subclass explicitly:

```python
from django_tenant_options.contrib.rest_framework.serializers import OptionSerializer

from myapp.models import TaskPriorityOption


class PriorityOptionSerializer(OptionSerializer):
    class Meta(OptionSerializer.Meta):
        model = TaskPriorityOption
```

There are matching `SelectionSerializer` and `selection_serializer_factory`.

## ViewSets and resolving the tenant

The package never assumes how you resolve a tenant from a request. Subclass the
base viewset, bind your model and serializer, and override `get_tenant`:

```python
from django_tenant_options.contrib.rest_framework.views import BaseOptionViewSet

from myapp.models import TaskPriorityOption


class PriorityOptionViewSet(BaseOptionViewSet):
    option_model = TaskPriorityOption
    serializer_class = PriorityOptionSerializer

    def get_tenant(self):
        # Resolve however your app identifies tenants.
        return self.request.user.tenant
```

`BaseOptionViewSet` is read-only and provides:

- `list` - all options available to the tenant.
- `selected` (`GET .../selected/`) - only the tenant's actively selected options.

`BaseSelectionViewSet` is read/write: listing returns the tenant's active
selections, creating sets the tenant automatically, and deleting performs a
soft-delete.

## Wiring URLs

```python
from django.urls import include
from django.urls import path

from django_tenant_options.contrib.rest_framework.routers import build_router

from myapp.api import PriorityOptionViewSet

router = build_router("priorities", PriorityOptionViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
]
```

## OpenAPI schema (drf-spectacular)

Decorate views with `maybe_extend_schema`, which applies
`drf_spectacular.utils.extend_schema` when drf-spectacular is installed and is a
no-op otherwise - so your views never take a hard dependency:

```python
from django_tenant_options.contrib.rest_framework.schema import maybe_extend_schema


class PriorityOptionViewSet(BaseOptionViewSet):
    @maybe_extend_schema(summary="List available priority options")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
```

## django-bolt (experimental)

A thin adapter registers GET endpoints for available and selected options on a
django-bolt app object. It is fully guarded and intentionally small:

```python
from django_tenant_options.contrib.bolt.app import register_option_routes

from myapp.models import TaskPriorityOption

register_option_routes(app, TaskPriorityOption, get_tenant=lambda request: request.tenant)
```
