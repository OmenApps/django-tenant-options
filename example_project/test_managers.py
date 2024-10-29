"""Test cases for the managers."""

import pytest

from example_project.example.models import TaskPriorityOption
from example_project.example.models import Tenant


@pytest.mark.django_db
class TestTenantOptionsManagers:
    """Test cases for the managers."""

    def test_create_mandatory_option(self):
        """Test creating a mandatory option."""
        TaskPriorityOption.objects.create_mandatory(name="Critical")
        option = TaskPriorityOption.objects.get(name="Critical")
        assert option.option_type == "dm"

    def test_create_custom_option_for_tenant(self):
        """Test creating a custom option for a tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        TaskPriorityOption.objects.create_for_tenant(tenant=tenant, name="Custom Priority")
        option = TaskPriorityOption.objects.get(name="Custom Priority", tenant=tenant)
        assert option.option_type == "cu"
        assert option.tenant == tenant

    def test_options_for_tenant(self):
        """Test retrieving options for a tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        TaskPriorityOption.objects.create_mandatory(name="Critical")
        TaskPriorityOption.objects.create_optional(name="Low")
        TaskPriorityOption.objects.create_for_tenant(tenant=tenant, name="Custom Priority")

        options = TaskPriorityOption.objects.options_for_tenant(tenant=tenant)
        assert len(options) == 3
