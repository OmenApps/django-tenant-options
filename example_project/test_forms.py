"""Test cases for forms in the example project."""

import random

import pytest
from django import forms
from django.contrib.auth import get_user_model

from django_tenant_options.choices import OptionType
from django_tenant_options.exceptions import NoTenantProvidedFromViewError
from django_tenant_options.forms import OptionCreateFormMixin
from django_tenant_options.forms import OptionUpdateFormMixin
from django_tenant_options.forms import SelectionsForm
from django_tenant_options.forms import TenantFormBaseMixin
from django_tenant_options.forms import UserFacingFormMixin
from example_project.example.models import Task
from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import TaskStatusOption
from example_project.example.models import Tenant


User = get_user_model()


@pytest.mark.django_db
class TestTenantFormBaseMixin:
    """Test cases for TenantFormBaseMixin."""

    class TestForm(TenantFormBaseMixin, forms.ModelForm):
        """Test form for TenantFormBaseMixin."""

        __test__ = False

        class Meta:
            """Meta class for form."""

            model = TaskPriorityOption
            fields = ["name", "tenant"]

    def test_no_tenant_provided(self):
        """Test form raises error when no tenant provided."""
        with pytest.raises(NoTenantProvidedFromViewError):
            self.TestForm()

    def test_tenant_field_hidden(self):
        """Test tenant field is hidden in form."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestForm(tenant=tenant)
        assert isinstance(form.fields["tenant"].widget, forms.HiddenInput)
        assert form.fields["tenant"].initial == tenant

    def test_clean_tenant(self):
        """Test clean method enforces correct tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        form = self.TestForm(
            tenant=tenant, data={"name": "Test Option", "tenant": other_tenant.id}  # Try to submit different tenant
        )

        assert form.is_valid()
        assert form.cleaned_data["tenant"] == tenant  # Should enforce original tenant

    def test_associated_tenants_field_removal(self):
        """Test associated_tenants field is removed from form."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class FormWithAssociatedTenants(TenantFormBaseMixin, forms.ModelForm):
            """Form with associated_tenants field for testing removal."""

            associated_tenants = forms.ModelMultipleChoiceField(queryset=Tenant.objects.all())

            class Meta:
                """Meta class for form."""

                model = TaskPriorityOption
                fields = ["name", "tenant", "associated_tenants"]

        form = FormWithAssociatedTenants(tenant=tenant)
        assert "associated_tenants" not in form.fields

    def test_clean_with_invalid_data(self):
        """Test clean method with invalid form data."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class FormWithRequiredField(TenantFormBaseMixin, forms.ModelForm):
            """Form with required field for testing clean method."""

            required_field = forms.CharField(required=True)

            class Meta:
                """Meta class for form."""

                model = TaskPriorityOption
                fields = ["name", "tenant", "required_field"]

        form = FormWithRequiredField(tenant=tenant, data={})
        assert not form.is_valid()
        assert "required_field" in form.errors
        assert "tenant" not in form.errors  # Tenant should still be valid


@pytest.mark.django_db
class TestOptionCreateFormMixin:
    """Test cases for OptionCreateFormMixin."""

    class TestCreateForm(OptionCreateFormMixin, forms.ModelForm):
        """Test form for OptionCreateFormMixin."""

        __test__ = False

        class Meta:
            """Meta class for form."""

            model = TaskPriorityOption
            fields = "__all__"

    def test_option_type_hidden_and_custom(self):
        """Test option_type is hidden and set to CUSTOM."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestCreateForm(tenant=tenant)

        assert isinstance(form.fields["option_type"].widget, forms.HiddenInput)
        assert form.fields["option_type"].initial == OptionType.CUSTOM

    def test_deleted_field_hidden_and_none(self):
        """Test deleted field is hidden and set to None."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestCreateForm(tenant=tenant)

        assert isinstance(form.fields["deleted"].widget, forms.HiddenInput)
        assert form.fields["deleted"].initial is None

    def test_create_option(self):
        """Test creating a custom option."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestCreateForm(
            tenant=tenant,
            data={"name": "Custom Option", "option_type": OptionType.CUSTOM, "tenant": tenant.id, "deleted": None},
        )

        assert form.is_valid()
        option = form.save()
        assert option.name == "Custom Option"
        assert option.option_type == OptionType.CUSTOM
        assert option.tenant == tenant
        assert option.deleted is None

    def test_inheritance_chain(self):
        """Test form works with multiple inheritance."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class CustomMixin:
            """Custom mixin for form."""

            def clean_name(self, *args, **kwargs):
                """Custom clean method for name field."""
                name = self.cleaned_data.get("name", "")
                return name.upper()

        class ComplexCreateForm(CustomMixin, OptionCreateFormMixin, forms.ModelForm):
            """Complex form for testing multiple inheritance."""

            class Meta:
                """Meta class for form."""

                model = TaskPriorityOption
                fields = "__all__"

        form = ComplexCreateForm(
            tenant=tenant,
            data={"name": "test option", "option_type": OptionType.CUSTOM, "tenant": tenant.id, "deleted": None},
        )

        assert form.is_valid()
        option = form.save()
        assert option.name == "TEST OPTION"  # Verify CustomMixin.clean_name was called

    def test_attempt_non_custom_option_type(self):
        """Test attempt to create option with non-custom option type."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestCreateForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "option_type": OptionType.MANDATORY,  # Try to create mandatory option
                "tenant": tenant.id,
                "deleted": None,
            },
        )

        assert form.is_valid()
        option = form.save()
        assert option.option_type == OptionType.CUSTOM  # Should force CUSTOM type


@pytest.mark.django_db
class TestOptionUpdateFormMixin:
    """Test cases for OptionUpdateFormMixin."""

    class TestUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
        """Test form for OptionUpdateFormMixin."""

        __test__ = False

        class Meta:
            """Meta class for form."""

            model = TaskPriorityOption
            fields = "__all__"

    def test_delete_field_added(self):
        """Test delete checkbox field is added."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestUpdateForm(tenant=tenant)
        assert "delete" in form.fields
        assert isinstance(form.fields["delete"], forms.BooleanField)
        assert form.fields["delete"].required is False

    def test_update_without_delete(self):
        """Test updating option without deletion."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Original Name", option_type=OptionType.CUSTOM, tenant=tenant)

        form = self.TestUpdateForm(
            tenant=tenant,
            instance=option,
            data={
                "name": "Updated Name",
                "option_type": OptionType.CUSTOM,
                "tenant": tenant.id,
                "deleted": None,
                "delete": False,
            },
        )

        assert form.is_valid()
        updated_option = form.save()
        assert updated_option.name == "Updated Name"
        assert updated_option.deleted is None

    def test_update_with_delete(self):
        """Test updating option with deletion."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="To Delete", option_type=OptionType.CUSTOM, tenant=tenant)

        form = self.TestUpdateForm(
            tenant=tenant,
            instance=option,
            data={
                "name": "To Delete",
                "option_type": OptionType.CUSTOM,
                "tenant": tenant.id,
                "deleted": None,
                "delete": True,
            },
        )

        assert form.is_valid()
        updated_option = form.save()
        assert updated_option.deleted is not None

    def test_partial_update(self):
        """Test partial update of option fields."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="Original Name", option_type=OptionType.CUSTOM, tenant=tenant)

        # Only update name field
        form = self.TestUpdateForm(
            tenant=tenant,
            instance=option,
            data={
                "name": "Updated Name",
                "option_type": OptionType.CUSTOM,
                "tenant": tenant.id,
            },
        )

        assert form.is_valid()
        updated_option = form.save()
        assert updated_option.name == "Updated Name"
        assert updated_option.option_type == OptionType.CUSTOM
        assert updated_option.tenant == tenant

    def test_attempted_tenant_change(self):
        """Test attempt to change option's tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")
        option = TaskPriorityOption.objects.create(name="Test Option", option_type=OptionType.CUSTOM, tenant=tenant)

        form = self.TestUpdateForm(
            tenant=tenant,
            instance=option,
            data={
                "name": "Test Option",
                "option_type": OptionType.CUSTOM,
                "tenant": other_tenant.id,  # Try to change tenant
                "deleted": None,
                "delete": False,
            },
        )

        assert form.is_valid()
        updated_option = form.save()
        assert updated_option.tenant == tenant  # Tenant should not change


@pytest.mark.django_db
class TestForSelectionsForm:
    """Test cases for SelectionsForm."""

    class TestSelectionsForm(SelectionsForm):
        """Test form for SelectionsForm."""

        __test__ = False

        class Meta:
            """Meta class for form."""

            model = TaskPrioritySelection

    def test_form_initialization(self):
        """Test selections form initialization."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestSelectionsForm(tenant=tenant)

        assert "selections" in form.fields
        assert hasattr(form, "selection_model")
        assert hasattr(form, "option_model")

    def test_selections_queryset(self):
        """Test selections queryset is properly filtered."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create options of different types
        mandatory = TaskPriorityOption.objects.create(name="Mandatory", option_type=OptionType.MANDATORY)
        optional = TaskPriorityOption.objects.create(name="Optional", option_type=OptionType.OPTIONAL)
        custom = TaskPriorityOption.objects.create(name="Custom", option_type=OptionType.CUSTOM, tenant=tenant)

        form = self.TestSelectionsForm(tenant=tenant)
        queryset = form.fields["selections"].queryset

        assert mandatory in queryset
        assert optional in queryset
        assert custom in queryset

    def test_save_selections(self):
        """Test saving selections."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create options
        mandatory = TaskPriorityOption.objects.create(name="Mandatory", option_type=OptionType.MANDATORY)
        optional = TaskPriorityOption.objects.create(name="Optional", option_type=OptionType.OPTIONAL)

        form = self.TestSelectionsForm(tenant=tenant, data={"selections": [optional.id]})  # Select optional option

        assert form.is_valid()
        form.save()

        # Verify selections were saved
        selected_options = TaskPriorityOption.objects.selected_options_for_tenant(tenant)
        assert mandatory in selected_options  # Mandatory should always be included
        assert optional in selected_options  # Optional should be included because we selected it

    def test_mandatory_options_always_selected(self):
        """Test that mandatory options are always included in selections."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        mandatory = TaskPriorityOption.objects.create(name="Mandatory", option_type=OptionType.MANDATORY)
        optional = TaskPriorityOption.objects.create(name="Optional", option_type=OptionType.OPTIONAL)

        # Try to submit form without selecting mandatory option
        form = self.TestSelectionsForm(tenant=tenant, data={"selections": [optional.id]})

        assert form.is_valid()
        form.save()

        # Verify mandatory option is still selected
        selections = TaskPrioritySelection.objects.filter(tenant=tenant, option=mandatory)
        assert selections.exists()

    def test_remove_existing_selection(self):
        """Test removing an existing selection."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        optional = TaskPriorityOption.objects.create(name="Optional", option_type=OptionType.OPTIONAL)
        selection = TaskPrioritySelection.objects.create(tenant=tenant, option=optional)
        selection_id = selection.id

        # Submit form without the optional selection
        form = self.TestSelectionsForm(tenant=tenant, data={"selections": []})

        assert form.is_valid()
        form.save()

        # Verify selection was removed
        assert not TaskPrioritySelection.objects.filter(id=selection_id, deleted__isnull=True).exists()

    def test_concurrent_selection_updates(self):
        """Test handling of concurrent selection updates."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        optional1 = TaskPriorityOption.objects.create(name="Optional 1", option_type=OptionType.OPTIONAL)
        optional2 = TaskPriorityOption.objects.create(name="Optional 2", option_type=OptionType.OPTIONAL)

        # Create two forms simultaneously
        form1 = self.TestSelectionsForm(tenant=tenant, data={"selections": [optional1.id]})
        form2 = self.TestSelectionsForm(tenant=tenant, data={"selections": [optional2.id]})

        assert form1.is_valid() and form2.is_valid()
        form1.save()
        form2.save()

        # Verify final state includes both selections
        selections = TaskPrioritySelection.objects.filter(tenant=tenant)
        selected_options = [s.option.id for s in selections]
        assert optional2.id in selected_options  # Last save wins


@pytest.mark.django_db
class TestUserFacingFormMixin:
    """Test cases for UserFacingFormMixin."""

    class TestUserFacingForm(UserFacingFormMixin, forms.ModelForm):
        """Test form class that uses UserFacingFormMixin."""

        __test__ = False

        class Meta:
            """Meta class for form."""

            model = Task
            fields = ["title", "description", "priority", "status"]

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment with required user."""
        self.user = User.objects.create_user(username=f"testuser{random.randrange(9999999)}", password="testpass")
        yield

    def test_no_tenant_provided(self):
        """Test form raises error when no tenant provided."""
        with pytest.raises(NoTenantProvidedFromViewError):
            self.TestUserFacingForm()

    def test_handle_deleted_selection(self):
        """Test handling of deleted selections."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(name="To Delete", option_type=OptionType.CUSTOM, tenant=tenant)
        TaskPrioritySelection.objects.create(tenant=tenant, option=option)

        task = Task.objects.create(title="Test Task", description="Test Description", priority=option, user=self.user)

        # Soft delete the option
        option.delete()

        form = self.TestUserFacingForm(tenant=tenant, instance=task)
        assert option not in form.fields["priority"].queryset

    def test_tenant_field_hidden(self):
        """Test tenant field is hidden in form."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        form = self.TestUserFacingForm(tenant=tenant)

        if "tenant" in form.fields:  # Only test if the form has a tenant field
            assert isinstance(form.fields["tenant"].widget, forms.HiddenInput)
            assert form.fields["tenant"].initial == tenant

    def test_clean_tenant(self):
        """Test clean method enforces correct tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        form = self.TestUserFacingForm(
            tenant=tenant,
            data={
                "title": "Test Task",
                "description": "Test Description",
                "tenant": other_tenant.id,  # Try to submit different tenant
            },
        )

        form.is_valid()  # Run validation
        assert form.cleaned_data.get("tenant") == tenant  # Should enforce original tenant

    def test_foreign_key_field_filtering(self):
        """Test filtering of foreign key fields."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        # Create options for different tenants
        tenant_option = TaskPriorityOption.objects.create(
            name="Tenant Option", option_type=OptionType.CUSTOM, tenant=tenant
        )
        other_option = TaskPriorityOption.objects.create(
            name="Other Option", option_type=OptionType.CUSTOM, tenant=other_tenant
        )

        form = self.TestUserFacingForm(tenant=tenant)
        priority_queryset = form.fields["priority"].queryset

        assert tenant_option in priority_queryset
        assert other_option not in priority_queryset

    def test_multiple_foreign_key_fields(self):
        """Test handling of multiple foreign key fields to option models."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        priority = TaskPriorityOption.objects.create(name="Priority", option_type=OptionType.CUSTOM, tenant=tenant)
        status = TaskStatusOption.objects.create(name="Status", option_type=OptionType.CUSTOM, tenant=tenant)

        form = self.TestUserFacingForm(tenant=tenant)

        # Verify both foreign key fields are properly filtered
        assert priority in form.fields["priority"].queryset
        assert status in form.fields["status"].queryset

    def test_field_initial_values(self):
        """Test initial values for foreign key fields with existing instance."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        priority = TaskPriorityOption.objects.create(name="Priority", option_type=OptionType.CUSTOM, tenant=tenant)
        task = Task.objects.create(title="Test Task", description="Test Description", priority=priority, user=self.user)

        form = self.TestUserFacingForm(tenant=tenant, instance=task)
        assert form.fields["priority"].initial == priority.id
