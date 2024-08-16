# Usage

## Installation

```bash
pip install django-tenant-options
```

## Configuration

1. Add `django_tenant_options` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    ...
    'django_tenant_options',
    ...
]
```

2. Set the `DJANGO_TENANT_OPTIONS` dictionary in your `settings.py`:

```python
DJANGO_TENANT_OPTIONS = {
    "TENANT_MODEL": "yourapp.Tenant",
}
```

For more information on the available settings, see the [`app_settings.py` reference](https://django-tenant-options.readthedocs.io/en/latest/reference.html#module-django_tenant_options.app_settings).
