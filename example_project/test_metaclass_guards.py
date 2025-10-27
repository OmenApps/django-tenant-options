"""Test metaclass guards to prevent duplicate field creation."""

import pytest


@pytest.mark.django_db
class TestMetaclassGuards:
    """Test that metaclasses properly guard against duplicate field creation."""

    def test_tenant_field_exists_on_option_models(self):
        """Test that tenant field is added to Option models."""
        from example_project.example.models import TaskPriorityOption

        # Verify tenant field exists
        assert hasattr(TaskPriorityOption, "tenant")

        # Verify it's in the model's fields
        field_names = [f.name for f in TaskPriorityOption._meta.get_fields()]
        assert "tenant" in field_names

        # Verify it only appears once
        assert field_names.count("tenant") == 1

    def test_option_field_exists_on_selection_models(self):
        """Test that option field is added to Selection models."""
        from example_project.example.models import TaskPrioritySelection

        # Verify option field exists
        assert hasattr(TaskPrioritySelection, "option")

        # Verify it's in the model's fields
        field_names = [f.name for f in TaskPrioritySelection._meta.get_fields()]
        assert "option" in field_names

        # Verify it only appears once
        assert field_names.count("option") == 1

    def test_associated_tenants_field_exists_on_option_models(self):
        """Test that associated_tenants field is added to Option models."""
        from example_project.example.models import TaskPriorityOption

        # Verify associated_tenants field exists
        assert hasattr(TaskPriorityOption, "associated_tenants")

        # Verify it's in the model's fields
        field_names = [f.name for f in TaskPriorityOption._meta.get_fields()]
        assert "associated_tenants" in field_names

        # Verify it only appears once
        assert field_names.count("associated_tenants") == 1

    def test_no_duplicate_fields_in_models(self):
        """Test that models don't have duplicate field names."""
        from example_project.example.models import TaskPriorityOption, TaskPrioritySelection

        # Check Option model for duplicate field names
        option_field_names = [f.name for f in TaskPriorityOption._meta.get_fields()]
        option_unique_fields = set(option_field_names)

        assert len(option_field_names) == len(
            option_unique_fields
        ), f"Option model has duplicate fields: {option_field_names}"

        # Check Selection model for duplicate field names
        selection_field_names = [f.name for f in TaskPrioritySelection._meta.get_fields()]
        selection_unique_fields = set(selection_field_names)

        assert len(selection_field_names) == len(
            selection_unique_fields
        ), f"Selection model has duplicate fields: {selection_field_names}"

        # Verify critical fields exist exactly once
        assert option_field_names.count("tenant") == 1, "tenant field should exist exactly once"
        assert option_field_names.count("associated_tenants") == 1, "associated_tenants should exist exactly once"
        assert selection_field_names.count("option") == 1, "option field should exist exactly once"
        assert selection_field_names.count("tenant") == 1, "tenant field should exist exactly once in Selection"

    def test_tenant_field_is_foreignkey(self):
        """Test that tenant field is a ForeignKey."""
        from django.db import models
        from example_project.example.models import TaskPriorityOption

        tenant_field = TaskPriorityOption._meta.get_field("tenant")

        # Should be a ForeignKey (or auto_prefetch.ForeignKey which inherits from it)
        assert isinstance(tenant_field, models.ForeignKey)

    def test_option_field_is_foreignkey(self):
        """Test that option field is a ForeignKey."""
        from django.db import models
        from example_project.example.models import TaskPrioritySelection

        option_field = TaskPrioritySelection._meta.get_field("option")

        # Should be a ForeignKey (or auto_prefetch.ForeignKey which inherits from it)
        assert isinstance(option_field, models.ForeignKey)

    def test_associated_tenants_field_is_manytomany(self):
        """Test that associated_tenants field is a ManyToManyField."""
        from django.db import models
        from example_project.example.models import TaskPriorityOption

        associated_tenants_field = TaskPriorityOption._meta.get_field("associated_tenants")

        # Should be a ManyToManyField
        assert isinstance(associated_tenants_field, models.ManyToManyField)

    def test_all_option_models_have_required_fields(self):
        """Test that all Option models have the required dynamically added fields."""
        from django_tenant_options.helpers import all_option_subclasses

        required_fields = ["tenant", "associated_tenants"]

        for model_class in all_option_subclasses():
            model_field_names = [f.name for f in model_class._meta.get_fields()]

            for required_field in required_fields:
                assert required_field in model_field_names, f"{model_class.__name__} missing {required_field}"

                # Verify no duplicates
                assert (
                    model_field_names.count(required_field) == 1
                ), f"{model_class.__name__} has duplicate {required_field}"

    def test_all_selection_models_have_required_fields(self):
        """Test that all Selection models have the required dynamically added fields."""
        from django_tenant_options.helpers import all_selection_subclasses

        required_fields = ["tenant", "option"]

        for model_class in all_selection_subclasses():
            model_field_names = [f.name for f in model_class._meta.get_fields()]

            for required_field in required_fields:
                assert required_field in model_field_names, f"{model_class.__name__} missing {required_field}"

                # Verify no duplicates
                assert (
                    model_field_names.count(required_field) == 1
                ), f"{model_class.__name__} has duplicate {required_field}"
