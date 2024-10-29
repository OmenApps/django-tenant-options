"""Test cases for the django-tenant-options package."""

import pytest
from django.apps import apps
from django.conf import settings
from django.forms import ModelMultipleChoiceField

from django_tenant_options.choices import OptionType
from django_tenant_options.form_fields import OptionsModelMultipleChoiceField
from django_tenant_options.helpers import all_selection_subclasses
from django_tenant_options.models import AbstractSelection
from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import Tenant


@pytest.fixture
def test_tenant(db):
    """Create a test tenant."""
    return Tenant.objects.create(
        name="Test Tenant",
        subdomain="test",
    )


def test_succeeds() -> None:
    """It exits with a status code of zero."""
    assert 0 == 0


def test_settings() -> None:
    """It exits with a status code of zero."""
    assert settings.USE_TZ is True


def test_apps() -> None:
    """It exits with a status code of zero."""
    assert "django_tenant_options" in apps.get_app_config("django_tenant_options").name


class TestOptionsModelMultipleChoiceField:
    """Tests for the OptionsModelMultipleChoiceField class."""

    def test_inheritance(self):
        """Test that OptionsModelMultipleChoiceField inherits from ModelMultipleChoiceField."""
        assert issubclass(OptionsModelMultipleChoiceField, ModelMultipleChoiceField)

    @pytest.mark.parametrize(
        "option_type,name,expected_label",
        [
            (OptionType.MANDATORY, "Test Option", "Test Option (mandatory)"),
            (OptionType.OPTIONAL, "Test Option", "Test Option (optional)"),
            (OptionType.CUSTOM, "Test Option", "Test Option (custom)"),
        ],
    )
    def test_label_from_instance(self, option_type, name, expected_label, test_tenant, db):
        """Test that label_from_instance returns the correct label based on option_type."""
        # Create an option instance with tenant for CUSTOM type
        option_data = {
            "name": name,
            "option_type": option_type,
        }

        # Only add tenant for CUSTOM options
        if option_type == OptionType.CUSTOM:
            option_data["tenant"] = test_tenant

        option = TaskPriorityOption.objects.create(**option_data)

        # Create the field instance
        field = OptionsModelMultipleChoiceField(queryset=TaskPriorityOption.objects.all())

        # Test the label generation
        assert field.label_from_instance(option) == expected_label


class TestHelpers:
    """Tests for helper functions."""

    def test_all_selection_subclasses(self, db):
        """Test that all_selection_subclasses returns all non-abstract subclasses."""
        subclasses = all_selection_subclasses()

        # Verify that TaskPrioritySelection is in the list
        assert TaskPrioritySelection in subclasses

        # Verify that AbstractSelection is not in the list
        assert AbstractSelection not in subclasses

        # All returned classes should be concrete (non-abstract) subclasses
        for cls in subclasses:
            assert issubclass(cls, AbstractSelection)
            assert not cls._meta.abstract

    def test_all_selection_subclasses_structure(self, db):
        """Test the structure of classes returned by all_selection_subclasses."""
        subclasses = all_selection_subclasses()

        for cls in subclasses:
            # Verify each subclass has required attributes
            assert hasattr(cls, "tenant_model")
            assert hasattr(cls, "option_model")

            # Verify each subclass has the correct model fields
            assert "tenant" in [f.name for f in cls._meta.fields]
            assert "option" in [f.name for f in cls._meta.fields]
            assert "deleted" in [f.name for f in cls._meta.fields]
