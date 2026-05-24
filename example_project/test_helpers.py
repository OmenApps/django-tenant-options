"""Test cases for django_tenant_options.helpers."""

import pytest

from django_tenant_options.helpers import get_default_option_names
from example_project.example.models import TaskPriorityOption


@pytest.mark.django_db
class TestGetDefaultOptionNames:
    """Test cases for get_default_option_names."""

    def test_returns_sorted_default_names(self):
        """Returns the default_options keys sorted alphabetically."""
        names = get_default_option_names(TaskPriorityOption)
        assert names == ["Critical", "High", "Low", "Medium"]

    def test_returns_empty_list_when_no_default_options(self):
        """Returns an empty list when the model has no default_options."""

        class FakeOption:
            default_options = {}

        assert get_default_option_names(FakeOption) == []

    def test_returns_empty_list_when_attribute_missing(self):
        """Returns an empty list when the model has no default_options attribute."""

        class FakeOption:
            pass

        assert get_default_option_names(FakeOption) == []
