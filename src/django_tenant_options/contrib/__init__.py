"""Optional, guarded integration extras for django-tenant-options.

Subpackages here (rest_framework, bolt) provide opt-in API integrations.
This package and its ``__init__`` intentionally import none of the optional
third-party libraries (DRF, drf-spectacular, django-bolt). The top-level
``django_tenant_options`` package never imports this subpackage, so the core
stays dependency-free.
"""
