"""Django REST Framework integration for django-tenant-options.

Importing the modules in this subpackage (serializers, views, routers)
requires ``djangorestframework`` to be installed. Install it via the extra::

    pip install django-tenant-options[drf]

The ``schema`` module additionally integrates with ``drf-spectacular`` when
it is installed, and degrades to a no-op when it is not.
"""
