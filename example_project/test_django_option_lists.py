"""Test cases for the django-tenant-options package."""

from django.apps import apps
from django.conf import settings


def test_succeeds() -> None:
    """It exits with a status code of zero."""
    assert 0 == 0


def test_settings() -> None:
    """It exits with a status code of zero."""
    assert settings.USE_TZ is True


def test_apps() -> None:
    """It exits with a status code of zero."""
    assert "django_tenant_options" in apps.get_app_config("django_tenant_options").name
