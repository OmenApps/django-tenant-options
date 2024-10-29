"""Test cases for the models."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction

from django_tenant_options.choices import OptionType
from django_tenant_options.exceptions import IncorrectSubclassError
from django_tenant_options.exceptions import InvalidDefaultOptionError
from django_tenant_options.models import validate_model_has_attribute
from django_tenant_options.models import validate_model_is_concrete
from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import Tenant


@pytest.mark.django_db
class TestTenantOptionsModels:
    """Test cases for the models."""

    def test_create_tenant(self):
        """Test creating a tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        assert tenant.name == "Test Tenant"
        assert tenant.subdomain == "test-tenant"

    def test_create_task_priority_option(self):
        """Test creating a task priority option."""
        Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Critical", option_type="dm")
        assert option.name == "Critical"
        assert option.option_type == "dm"

    def test_create_task_priority_selection(self):
        """Test creating a task priority selection."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Major", option_type="dm")
        selection = TaskPrioritySelection.objects.create(tenant=tenant, option=option)
        assert selection.tenant == tenant
        assert selection.option == option

    def test_uniqueness_of_two_custom_option_names(self):
        """Test the uniqueness of option names."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        TaskPriorityOption.objects.create(name="Major", option_type="cu", tenant=tenant)

        with pytest.raises(IntegrityError):
            TaskPriorityOption.objects.create(name="Major", option_type="cu", tenant=tenant)

    def test_uniqueness_of_custom_and_other_option_names(self):
        """Test the uniqueness of option names."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        TaskPriorityOption.objects.create(name="Major", option_type="dm")

        with pytest.raises(ValidationError):
            TaskPriorityOption.objects.create(name="Major", option_type="cu", tenant=tenant)

    def test_check_constraint_on_custom_options(self):
        """Test the check constraint on custom options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Test creating without tenant - should fail
        try:
            with transaction.atomic():
                TaskPriorityOption.objects.create(name="Custom Option", option_type="cu")
            pytest.fail("Should have raised an IntegrityError")
        except IntegrityError:
            pass

        # Test creating with tenant - should succeed
        option = TaskPriorityOption.objects.create(name="Custom Option", option_type="cu", tenant=tenant)
        assert option.tenant == tenant
        assert option.name == "Custom Option"
        assert option.option_type == "cu"


@pytest.mark.django_db
class TestOptionModel:
    """Test cases for the AbstractOption functionalities."""

    def test_soft_delete_behavior(self):
        """Test soft delete functionality of options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)

        # Test soft delete
        option.delete()
        assert option.deleted is not None
        assert TaskPriorityOption.objects.filter(id=option.id).exists()

        # Test that soft-deleted options are excluded from active queryset
        assert not TaskPriorityOption.objects.active().filter(id=option.id).exists()
        assert TaskPriorityOption.objects.deleted().filter(id=option.id).exists()

    def test_queryset_methods(self):
        """Test custom queryset methods."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create different types of options
        mandatory = TaskPriorityOption.objects.create(name="Mandatory", option_type=OptionType.MANDATORY)
        optional = TaskPriorityOption.objects.create(name="Optional", option_type=OptionType.OPTIONAL)
        custom = TaskPriorityOption.objects.create(name="Custom", option_type=OptionType.CUSTOM, tenant=tenant)

        # Test custom_options() method
        custom_options = TaskPriorityOption.objects.custom_options()
        assert custom in custom_options
        assert mandatory not in custom_options
        assert optional not in custom_options

    def test_default_options_sync(self):
        """Test syncing of default options."""
        # Make sure default options have been created
        initial_options = TaskPriorityOption.objects._update_default_options()

        # initial_options = set(TaskPriorityOption.objects.values_list('name', flat=True))
        assert "High" in initial_options  # From default_options in model
        assert "Low" in initial_options  # From default_options in model

        # Verify all default options exist
        # for name in TaskPriorityOption.default_options.keys():
        for name in TaskPriorityOption.default_options:
            assert TaskPriorityOption.objects.filter(name=name).exists()

    def test_multiple_tenant_options(self):
        """Test options behavior with multiple tenants."""
        tenant1 = Tenant.objects.create(name="Tenant 1", subdomain="tenant1")
        tenant2 = Tenant.objects.create(name="Tenant 2", subdomain="tenant2")

        # Create custom options for each tenant
        option1 = TaskPriorityOption.objects.create(name="Custom 1", option_type=OptionType.CUSTOM, tenant=tenant1)
        option2 = TaskPriorityOption.objects.create(name="Custom 2", option_type=OptionType.CUSTOM, tenant=tenant2)

        # Test options_for_tenant
        tenant1_options = TaskPriorityOption.objects.options_for_tenant(tenant1)
        assert option1 in tenant1_options
        assert option2 not in tenant1_options

        # Test mandatory options appear for both tenants
        mandatory = TaskPriorityOption.objects.create(name="Mandatory Test", option_type=OptionType.MANDATORY)
        assert mandatory in TaskPriorityOption.objects.options_for_tenant(tenant1)
        assert mandatory in TaskPriorityOption.objects.options_for_tenant(tenant2)

    def test_undelete_functionality(self):
        """Test undelete functionality of options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)

        # Delete and verify
        option.delete()
        assert option.deleted is not None

        # Test undelete through queryset method
        TaskPriorityOption.objects.filter(id=option.id).undelete()
        option.refresh_from_db()
        assert option.deleted is None
        assert TaskPriorityOption.objects.active().filter(id=option.id).exists()

    def test_override_delete_functionality(self):
        """Test override delete functionality."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)
        option_id = option.id

        # Test hard delete with override
        option.delete(override=True)

        assert not TaskPriorityOption.objects.filter(id=option_id).exists()

    def test_str_representation(self):
        """Test string representation of option models."""
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.MANDATORY)
        assert str(option) == "Test Option"

    def test_concurrent_option_creation(self):
        """Test handling of concurrent option creation."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Try to create options with same name concurrently
        with transaction.atomic():
            TaskPriorityOption.objects.create(name="Concurrent Test", option_type=OptionType.CUSTOM, tenant=tenant)

            with pytest.raises(IntegrityError):
                TaskPriorityOption.objects.create(name="Concurrent Test", option_type=OptionType.CUSTOM, tenant=tenant)

    def test_case_insensitive_name_uniqueness(self):
        """Test case-insensitive uniqueness of option names."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)

        # Try to create option with same name but different case
        with pytest.raises(IntegrityError):
            TaskPriorityOption.objects.create(name="TEST OPTION", option_type=OptionType.CUSTOM, tenant=tenant)

    def test_update_default_options_with_changes(self):
        """Test updating default options when definitions change."""
        # Create an option that's not in default_options
        extra_option = TaskPriorityOption.objects.create(name="Extra Option", option_type=OptionType.MANDATORY)

        # Update default options - should soft delete extra option
        TaskPriorityOption.objects._update_default_options()

        extra_option.refresh_from_db()
        assert extra_option.deleted is not None

        # Verify all default options still exist
        # for name in TaskPriorityOption.default_options.keys():
        for name in TaskPriorityOption.default_options:
            assert TaskPriorityOption.objects.active().filter(name=name).exists()


@pytest.mark.django_db
class TestSelectionModel:
    """Test cases for the AbstractSelection functionalities."""

    def test_selection_constraints(self):
        """Test selection model constraints."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        custom_option = TaskPriorityOption.objects.create(name="Custom", option_type=OptionType.CUSTOM, tenant=tenant)

        # Test that a tenant can't select another tenant's custom option
        with pytest.raises(ValueError):
            TaskPrioritySelection.objects.create(tenant=other_tenant, option=custom_option)

    def test_selection_soft_delete(self):
        """Test soft delete behavior of selections."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)
        selection = TaskPrioritySelection.objects.create(tenant=tenant, option=option)

        # Test soft delete
        selection.delete()
        selection.refresh_from_db()

        assert selection.deleted is not None
        assert not TaskPrioritySelection.objects.active().filter(id=selection.id).exists()

    def test_selected_options_for_tenant(self):
        """Test retrieving selected options for a tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create and select different types of options
        mandatory = TaskPriorityOption.objects.create(name="Mandatory Test", option_type=OptionType.MANDATORY)
        optional = TaskPriorityOption.objects.create(name="Optional Test", option_type=OptionType.OPTIONAL)
        custom = TaskPriorityOption.objects.create(name="Custom Test", option_type=OptionType.CUSTOM, tenant=tenant)

        # Create selections
        TaskPrioritySelection.objects.create(tenant=tenant, option=optional)
        TaskPrioritySelection.objects.create(tenant=tenant, option=custom)

        selected_options = TaskPriorityOption.objects.selected_options_for_tenant(tenant)

        # Mandatory options should always be included
        assert mandatory in selected_options
        # Optional and custom options should be included only if selected
        assert optional in selected_options
        assert custom in selected_options

    def test_selection_cascade_on_option_delete(self):
        """Test selection behavior when related option is deleted."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)
        selection = TaskPrioritySelection.objects.create(tenant=tenant, option=option)
        selection_id = selection.id

        # When option is soft-deleted
        option.delete()
        selection.refresh_from_db()
        assert selection.deleted is None  # Selection should remain active

        # When option is hard-deleted
        option.delete(override=True)
        # Selections are cascade deleted as well when we hard-delete an option
        assert not TaskPrioritySelection.objects.filter(id=selection_id).exists()

    def test_bulk_selection_operations(self):
        """Test bulk operations on selections."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create multiple options and selections
        options = [
            TaskPriorityOption.objects.create(name=f"Option {i}", option_type=OptionType.CUSTOM, tenant=tenant)
            for i in range(3)
        ]

        selections = [TaskPrioritySelection.objects.create(tenant=tenant, option=option) for option in options]

        # Test bulk soft delete
        TaskPrioritySelection.objects.filter(id__in=[s.id for s in selections]).delete()

        # Verify all selections are soft deleted
        for selection in selections:
            selection.refresh_from_db()
            assert selection.deleted is not None

        # Test bulk undelete
        TaskPrioritySelection.objects.filter(id__in=[s.id for s in selections]).undelete()

        # Verify all selections are active again
        for selection in selections:
            selection.refresh_from_db()
            assert selection.deleted is None

    def test_create_selection_for_deleted_option(self):
        """Test creating selection for a soft-deleted option."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)

        # Soft delete the option
        option.delete()

        # Try to create selection for deleted option
        # Should succeed since option still exists in database
        selection = TaskPrioritySelection.objects.create(tenant=tenant, option=option)
        assert selection.id is not None


@pytest.mark.django_db
class TestValidationFunctions:
    """Test cases for the validation helper functions."""

    def test_validate_model_is_concrete(self):
        """Test validation of concrete models."""
        from django.db.models import Model

        # Create a test abstract model
        class AbstractTestModel(Model):
            """Test abstract model."""

            class Meta:
                """Meta class."""

                abstract = True

        # Test that validation fails for abstract model
        with pytest.raises(IncorrectSubclassError):
            validate_model_is_concrete(AbstractTestModel)

        # Test that validation passes for concrete model
        validate_model_is_concrete(TaskPriorityOption)

    def test_validate_model_has_attribute(self):
        """Test validation of model attributes."""
        # Test with existing attribute
        validate_model_has_attribute(TaskPriorityOption, "selection_model")

        # Test with non-existent attribute
        with pytest.raises(AttributeError):
            validate_model_has_attribute(TaskPriorityOption, "nonexistent_attr")

        # Test with wrong attribute type
        with pytest.raises(AttributeError):
            validate_model_has_attribute(TaskPriorityOption, "selection_model", attr_type=int)


@pytest.mark.django_db
class TestOptionManagerMethods:
    """Test cases for option manager methods."""

    def test_create_for_tenant_validation(self):
        """Test validation in create_for_tenant method."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Try to create option with same name as existing mandatory option
        TaskPriorityOption.objects.create_mandatory(name="Mandatory Test")

        with pytest.raises(ValidationError):
            TaskPriorityOption.objects.create_for_tenant(tenant=tenant, name="Mandatory Test")

    def test_manager_create_methods(self):
        """Test all creation methods in the manager."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Test create_mandatory
        mandatory = TaskPriorityOption.objects.create_mandatory("Mandatory Test")
        assert mandatory.option_type == OptionType.MANDATORY
        assert mandatory.tenant is None

        # Test create_optional
        optional = TaskPriorityOption.objects.create_optional("Optional Test")
        assert optional.option_type == OptionType.OPTIONAL
        assert optional.tenant is None

        # Test create_for_tenant
        custom = TaskPriorityOption.objects.create_for_tenant(tenant, "Custom Test")
        assert custom.option_type == OptionType.CUSTOM
        assert custom.tenant == tenant

    def test_update_default_option_validation(self):
        """Test validation in _update_or_create_default_option method."""
        # Try to create default option with invalid option_type
        with pytest.raises(InvalidDefaultOptionError):
            TaskPriorityOption.objects._update_or_create_default_option("Test Option", {"option_type": "invalid"})

    def test_options_for_tenant_with_deleted(self):
        """Test options_for_tenant including deleted options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create and soft-delete an option
        option = TaskPriorityOption.objects.create(name="Deleted Option", option_type=OptionType.CUSTOM, tenant=tenant)
        option.delete()

        # Test without deleted options
        assert option not in TaskPriorityOption.objects.options_for_tenant(tenant)

        # Test including deleted options
        assert option in TaskPriorityOption.objects.options_for_tenant(tenant, include_deleted=True)
