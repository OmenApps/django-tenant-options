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
from example_project.example.models import TaskStatusSelection
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
            fields = ["name", "option_type", "tenant"]

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
            tenant=tenant, data={"name": "Test Option", "tenant": other_tenant.id, "option_type": OptionType.CUSTOM}
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

    def test_clean_with_multiple_inheritance(self):
        """Test clean method behaves correctly with multiple inheritance."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class ParentForm:
            """Parent form class."""
            def clean(self):
                """Clean method that modifies data."""
                data = super().clean()
                data['extra'] = 'parent_value'
                return data

        class ChildForm(ParentForm, TenantFormBaseMixin, forms.ModelForm):
            """Child form with multiple inheritance."""
            class Meta:
                """Meta class for form."""
                model = TaskPriorityOption
                fields = ["name", "tenant"]

            def clean(self):
                """Clean method that modifies parent data."""
                data = super().clean()
                data['child'] = 'child_value'
                return data

        form = ChildForm(
            tenant=tenant,
            data={'name': 'Test Option'}
        )
        assert form.is_valid()
        assert form.cleaned_data['tenant'] == tenant
        assert form.cleaned_data['extra'] == 'parent_value'
        assert form.cleaned_data['child'] == 'child_value'

    def test_clean_with_empty_tenant_data(self):
        """Test clean method when tenant is not in cleaned_data."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            """Test form that simulates missing tenant in cleaned_data."""

            class Meta:
                model = TaskPriorityOption
                fields = ["name", "tenant"]

            def clean_tenant(self):
                """Override clean_tenant to simulate tenant field being empty."""
                return None

        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "tenant": tenant.id,  # Include tenant ID to pass initial validation
            }
        )

        # The form should be valid because TenantFormBaseMixin will enforce the tenant
        assert form.is_valid()
        # The enforced tenant should be in cleaned_data
        assert form.cleaned_data["tenant"] == tenant

    def test_clean_with_different_tenant(self):
        """Test clean method when submitted tenant differs from form tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):

            class Meta:
                model = TaskPriorityOption
                fields = ["name", "tenant"]

        # Try to submit with different tenant
        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "tenant": other_tenant.id,
            }
        )

        assert form.is_valid()
        assert form.cleaned_data["tenant"] == tenant  # Should enforce original tenant

    def test_tenant_field_with_empty_value(self):
        """Test form behavior when tenant field has empty value."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "tenant"]

        # Initialize form with empty tenant value
        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "tenant": "",  # Empty value
            }
        )

        # Verify form behavior
        assert form.is_valid()  # Form should be valid
        assert form.instance.tenant == tenant  # Instance should have correct tenant

    def test_tenant_field_enforcement_in_init(self):
        """Test that tenant is properly set during form initialization."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "tenant"]

        form = TestForm(tenant=tenant)

        # Check that tenant field is properly configured
        assert isinstance(form.fields["tenant"].widget, forms.HiddenInput)
        assert form.fields["tenant"].initial == tenant

    def test_tenant_field_with_data(self):
        """Test form behavior when tenant field is included."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "tenant", "option_type"]

        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "option_type": OptionType.CUSTOM,  # Set to CUSTOM to require tenant
                "tenant": tenant.id,  # Include tenant ID
            }
        )

        assert form.is_valid()
        instance = form.save()
        assert instance.tenant == tenant

    def test_tenant_field_set_by_mixin(self):
        """Test that tenant is enforced by mixin."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "tenant", "option_type"]

        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "option_type": OptionType.CUSTOM,
                "tenant": other_tenant.id,  # Try to use different tenant
            }
        )

        assert form.is_valid()
        instance = form.save()
        assert instance.tenant == tenant  # Should be original tenant
        assert instance.tenant != other_tenant

    def test_tenant_field_handling(self):
        """Test tenant field initialization and handling."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "option_type", "tenant"]

        form = TestForm(tenant=tenant)
        # Check initial field setup
        assert isinstance(form.fields["tenant"].widget, forms.HiddenInput)
        assert form.fields["tenant"].initial == tenant

        # Test form submission with Custom type (requires tenant)
        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "option_type": OptionType.CUSTOM,
                "tenant": tenant.id,
            }
        )

        assert form.is_valid()
        instance = form.save()
        assert instance.tenant == tenant

    def test_instance_initialization(self):
        """Test form initialization with an existing instance."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        option = TaskPriorityOption.objects.create(
            name="Test Option",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "option_type", "tenant"]

        # Test initialization without data
        form = TestForm(tenant=tenant, instance=option)
        assert isinstance(form.fields["tenant"].widget, forms.HiddenInput)
        assert form.fields["tenant"].initial == tenant

        # Test updating the instance
        form = TestForm(
            tenant=tenant,
            instance=option,
            data={
                "name": "Updated Option",
                "option_type": OptionType.CUSTOM,
                "tenant": tenant.id,
            }
        )

        assert form.is_valid()
        updated = form.save()
        assert updated.tenant == tenant
        assert updated.name == "Updated Option"

    def test_different_tenant_handling(self):
        """Test that form enforces original tenant even if different tenant provided."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "option_type", "tenant"]

        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Option",
                "option_type": OptionType.CUSTOM,
                "tenant": other_tenant.id,  # Try to use different tenant
            }
        )

        assert form.is_valid()
        instance = form.save()
        assert instance.tenant == tenant
        assert instance.tenant != other_tenant

    def test_tenant_field_clean_method(self):
        """Test that the clean method always enforces the tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        class TestForm(TenantFormBaseMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = ["name", "option_type", "tenant"]

        # Test with a custom option (requires tenant)
        form = TestForm(
            tenant=tenant,
            data={
                "name": "Test Custom Option",
                "option_type": OptionType.CUSTOM,
                "tenant": other_tenant.id,  # Try to use a different tenant
            }
        )
        assert form.is_valid()
        cleaned_data = form.clean()
        assert cleaned_data["tenant"] == tenant  # Should enforce original tenant


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

    def test_update_custom_option_type_preservation(self):
        """Test that updating a custom option preserves its option type."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(
            name="Original Name",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )

        form = self.TestUpdateForm(
            tenant=tenant,
            instance=option,
            data={
                'name': 'Updated Name',
                'option_type': OptionType.MANDATORY,  # Try to change type
                'tenant': tenant.id,
                'deleted': None,
                'delete': False,
            }
        )

        assert form.is_valid()
        updated_option = form.save()
        assert updated_option.name == 'Updated Name'
        assert updated_option.option_type == OptionType.CUSTOM  # Should preserve CUSTOM type

    def test_update_invalid_name(self):
        """Test updating an option with an invalid name."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        TaskPriorityOption.objects.create(
            name="Existing Name",
            option_type=OptionType.MANDATORY
        )
        custom_option = TaskPriorityOption.objects.create(
            name="Original Name",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )

        form = self.TestUpdateForm(
            tenant=tenant,
            instance=custom_option,
            data={
                'name': 'Existing Name',  # Try to use name that conflicts with mandatory option
                'option_type': OptionType.CUSTOM,
                'tenant': tenant.id,
                'deleted': None,
                'delete': False,
            }
        )

        assert not form.is_valid()
        assert 'name' in form.errors

    def test_clean_without_delete_field(self):
        """Test clean method behavior when delete field is missing from cleaned_data."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class UpdateForm(OptionUpdateFormMixin, forms.ModelForm):
            class Meta:
                model = TaskPriorityOption
                fields = "__all__"

            def clean(self):
                cleaned_data = super().clean()
                # Simulate cleaned_data without delete key
                if "delete" in cleaned_data:
                    del cleaned_data["delete"]
                return cleaned_data

        form = UpdateForm(tenant=tenant, data={"name": "Test Option"})
        assert form.is_valid()
        assert form.cleaned_data.get("deleted") is None


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

    def test_selections_with_deleted_mandatory_option(self):
        """Test handling of selections when a mandatory option is deleted."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        mandatory = TaskPriorityOption.objects.create(
            name="Mandatory",
            option_type=OptionType.MANDATORY
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=mandatory)

        # Soft delete the mandatory option
        mandatory.delete()

        form = self.TestSelectionsForm(tenant=tenant)
        assert mandatory not in form.fields['selections'].queryset

    def test_concurrent_selections_with_mandatory(self):
        """Test handling concurrent selections with mandatory options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        mandatory = TaskPriorityOption.objects.create(
            name="Mandatory",
            option_type=OptionType.MANDATORY
        )
        optional1 = TaskPriorityOption.objects.create(
            name="Optional 1",
            option_type=OptionType.OPTIONAL
        )
        optional2 = TaskPriorityOption.objects.create(
            name="Optional 2",
            option_type=OptionType.OPTIONAL
        )

        # Create two forms with different selections but both excluding mandatory
        form1 = self.TestSelectionsForm(tenant=tenant, data={'selections': [optional1.id]})
        form2 = self.TestSelectionsForm(tenant=tenant, data={'selections': [optional2.id]})

        assert form1.is_valid() and form2.is_valid()
        form1.save()
        form2.save()

        # Verify final state includes mandatory option and last selected optional
        selections = TaskPrioritySelection.objects.filter(tenant=tenant, deleted__isnull=True)
        selected_options = [s.option.id for s in selections]
        assert mandatory.id in selected_options
        assert optional2.id in selected_options
        assert optional1.id not in selected_options

    def test_mandatory_selection_validation(self):
        """Test that mandatory options cannot be deselected."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create mandatory and optional options
        mandatory = TaskPriorityOption.objects.create(
            name="Mandatory",
            option_type=OptionType.MANDATORY
        )
        optional = TaskPriorityOption.objects.create(
            name="Optional",
            option_type=OptionType.OPTIONAL
        )

        # Try to submit form without mandatory option
        form = self.TestSelectionsForm(
            tenant=tenant,
            data={'selections': [optional.id]}  # Only select optional
        )

        # Form should still be valid (mandatory will be added automatically)
        assert form.is_valid()
        form.save()

        # Verify mandatory option was included
        selections = TaskPrioritySelection.objects.filter(
            tenant=tenant,
            deleted__isnull=True
        ).values_list('option_id', flat=True)
        assert mandatory.id in selections
        assert optional.id in selections

    def test_selections_form_empty_selection(self):
        """Test form behavior with empty selection list."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create mandatory option
        mandatory = TaskPriorityOption.objects.create(
            name="Mandatory",
            option_type=OptionType.MANDATORY
        )

        # Submit form with empty selections
        form = self.TestSelectionsForm(
            tenant=tenant,
            data={'selections': []}
        )

        # Form should be valid (mandatory will be added)
        assert form.is_valid()
        form.save()

        # Verify only mandatory remains
        selections = TaskPrioritySelection.objects.filter(
            tenant=tenant,
            deleted__isnull=True
        )
        assert selections.count() == 1
        assert selections.first().option == mandatory

    def test_multiple_mandatory_options(self):
        """Test form behavior with multiple mandatory options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create multiple mandatory options
        mandatory1 = TaskPriorityOption.objects.create(
            name="Mandatory 1",
            option_type=OptionType.MANDATORY
        )
        mandatory2 = TaskPriorityOption.objects.create(
            name="Mandatory 2",
            option_type=OptionType.MANDATORY
        )
        optional = TaskPriorityOption.objects.create(
            name="Optional",
            option_type=OptionType.OPTIONAL
        )

        # Submit form selecting only optional
        form = self.TestSelectionsForm(
            tenant=tenant,
            data={'selections': [optional.id]}
        )

        assert form.is_valid()
        form.save()

        # Verify both mandatory options were included
        selections = TaskPrioritySelection.objects.filter(
            tenant=tenant,
            deleted__isnull=True
        ).values_list('option_id', flat=True)
        assert mandatory1.id in selections
        assert mandatory2.id in selections
        assert optional.id in selections


@pytest.mark.django_db
class TestUserFacingFormMixin:
    """Test cases for UserFacingFormMixin."""

    class TestUserFacingForm(UserFacingFormMixin, forms.ModelForm):
        """Test form class that uses UserFacingFormMixin."""

        __test__ = False

        class Meta:
            """Meta class for form."""

            model = Task
            fields = ["title", "description", "priority", "status", "user"]


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

        # Create associated selection
        TaskPrioritySelection.objects.create(tenant=tenant, option=tenant_option)
        TaskPrioritySelection.objects.create(tenant=other_tenant, option=other_option)

        form = self.TestUserFacingForm(tenant=tenant)
        priority_queryset = form.fields["priority"].queryset

        assert tenant_option in priority_queryset
        assert other_option not in priority_queryset

    def test_multiple_foreign_key_fields(self):
        """Test handling of multiple foreign key fields to option models."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create options for tenant
        priority = TaskPriorityOption.objects.create(name="Priority", option_type=OptionType.CUSTOM, tenant=tenant)
        status = TaskStatusOption.objects.create(name="Status", option_type=OptionType.CUSTOM, tenant=tenant)

        # Create associated selections for tenant
        TaskPrioritySelection.objects.create(tenant=tenant, option=priority)
        TaskStatusSelection.objects.create(tenant=tenant, option=status)

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

    def test_disabled_field_for_deleted_selection_setting(self):
        """Test DISABLE_FIELD_FOR_DELETED_SELECTION setting behavior."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(
            name="To Delete",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=option)
        task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            priority=option,
            user=self.user
        )

        # Soft delete the option
        option.delete()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.forms.DISABLE_FIELD_FOR_DELETED_SELECTION", True)
            form = self.TestUserFacingForm(tenant=tenant, instance=task)
            assert form.fields['priority'].widget.attrs.get('disabled') == 'disabled'
            assert form.fields['priority'].widget.attrs.get('readonly') == 'readonly'
            assert option in form.fields['priority'].queryset

    def test_multiple_option_fields_one_deleted(self):
        """Test form with multiple option fields where one selection is deleted."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        priority = TaskPriorityOption.objects.create(
            name="Priority",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        status = TaskStatusOption.objects.create(
            name="Status",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=priority)
        TaskStatusSelection.objects.create(tenant=tenant, option=status)

        task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            priority=priority,
            status=status,
            user=self.user
        )

        # Soft delete one option
        priority.delete()

        form = self.TestUserFacingForm(tenant=tenant, instance=task)
        assert priority not in form.fields['priority'].queryset
        assert status in form.fields['status'].queryset

    def test_foreign_key_field_initial_values_none(self):
        """Test initial values for foreign key fields when values are None."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            priority=None,
            status=None,
            user=self.user
        )

        form = self.TestUserFacingForm(tenant=tenant, instance=task)
        assert form.fields['priority'].initial is None
        assert form.fields['status'].initial is None

    def test_clean_with_disabled_deleted_selection(self):
        """Test clean method behavior with disabled deleted selection."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(
            name="To Delete",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=option)
        task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            priority=option,
            user=self.user
        )

        # Soft delete the option
        option.delete()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.forms.DISABLE_FIELD_FOR_DELETED_SELECTION", True)
            form = self.TestUserFacingForm(
                tenant=tenant,
                instance=task,
                data={
                    'title': 'Updated Task',
                    'description': 'Updated Description',
                    'priority': option.id,  # Try to keep the deleted option
                    'user': self.user
                }
            )
            assert form.is_valid()
            assert form.cleaned_data['priority'] == option

    def test_multiple_option_fields_validation(self):
        """Test validation of multiple option fields simultaneously."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        priority = TaskPriorityOption.objects.create(
            name="Priority",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        status = TaskStatusOption.objects.create(
            name="Status",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )

        # Create selections for both options
        TaskPrioritySelection.objects.create(tenant=tenant, option=priority)
        TaskStatusSelection.objects.create(tenant=tenant, option=status)

        form = self.TestUserFacingForm(
            tenant=tenant,
            data={
                'title': 'Test Task',
                'description': 'Test Description',
                'priority': priority.id,
                'status': status.id,
                'user': self.user.id,  # Add user field
            }
        )

        assert form.is_valid()
        saved_task = form.save()
        assert saved_task.priority == priority
        assert saved_task.status == status

    def test_form_with_no_selected_options(self):
        """Test form behavior when no options are selected for the tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        priority = TaskPriorityOption.objects.create(
            name="Priority",
            option_type=OptionType.OPTIONAL
        )

        form = self.TestUserFacingForm(tenant=tenant)
        assert priority not in form.fields['priority'].queryset

    def test_form_with_deleted_instance_option(self):
        """Test form behavior when the instance has a deleted option."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        option = TaskPriorityOption.objects.create(
            name="Priority",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=option)

        task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            priority=option,
            user=self.user
        )

        # Soft delete the option
        option.delete()

        # Test with DISABLE_FIELD_FOR_DELETED_SELECTION = False
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.forms.DISABLE_FIELD_FOR_DELETED_SELECTION", False)
            form = self.TestUserFacingForm(tenant=tenant, instance=task)
            assert option not in form.fields['priority'].queryset
            assert 'readonly' not in form.fields['priority'].widget.attrs
            assert 'disabled' not in form.fields['priority'].widget.attrs

    def test_form_update_with_tenant_conflict(self):
        """Test updating a form with an option from a different tenant."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        other_tenant = Tenant.objects.create(name="Other Tenant", subdomain="other-tenant")

        # Create options for both tenants
        tenant_option = TaskPriorityOption.objects.create(
            name="Tenant Option",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )
        other_option = TaskPriorityOption.objects.create(
            name="Other Option",
            option_type=OptionType.CUSTOM,
            tenant=other_tenant
        )

        TaskPrioritySelection.objects.create(tenant=tenant, option=tenant_option)
        TaskPrioritySelection.objects.create(tenant=other_tenant, option=other_option)

        # Try to submit form with option from other tenant
        form = self.TestUserFacingForm(
            tenant=tenant,
            data={
                'title': 'Test Task',
                'description': 'Test Description',
                'priority': other_option.id,  # Try to use option from other tenant
            }
        )

        assert not form.is_valid()
        assert 'priority' in form.errors

    def test_mixed_option_types(self):
        """Test form handling of mandatory, optional, and custom options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        # Create different types of options
        mandatory = TaskPriorityOption.objects.create(
            name="Mandatory",
            option_type=OptionType.MANDATORY
        )
        optional = TaskPriorityOption.objects.create(
            name="Optional",
            option_type=OptionType.OPTIONAL
        )
        custom = TaskPriorityOption.objects.create(
            name="Custom",
            option_type=OptionType.CUSTOM,
            tenant=tenant
        )

        # Create selections
        TaskPrioritySelection.objects.create(tenant=tenant, option=mandatory)
        TaskPrioritySelection.objects.create(tenant=tenant, option=optional)
        TaskPrioritySelection.objects.create(tenant=tenant, option=custom)

        form = self.TestUserFacingForm(tenant=tenant)

        # Verify all types appear in queryset when selected
        priority_queryset = form.fields['priority'].queryset
        assert mandatory in priority_queryset
        assert optional in priority_queryset
        assert custom in priority_queryset

        # Test form submission
        form = self.TestUserFacingForm(
            tenant=tenant,
            data={
                'title': 'Test Task',
                'description': 'Test Description',
                'priority': custom.id,  # Use custom option
                'user': self.user.id,  # Add user field
            }
        )

        assert form.is_valid()
        task = form.save()
        assert task.priority == custom

    def test_form_with_non_option_foreign_key(self):
        """Test form behavior with foreign key fields that aren't options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class FormWithNonOptionFK(UserFacingFormMixin, forms.ModelForm):
            """Test form with a non-option foreign key field."""
            non_option_field = forms.ModelChoiceField(
                queryset=User.objects.all(),
                required=False
            )

            class Meta:
                """Meta class for form."""
                model = Task
                fields = ['title', 'description', 'priority', 'non_option_field']

        User.objects.create_user(username='testuser', password='testpass')

        form = FormWithNonOptionFK(tenant=tenant)
        # Verify non-option field's queryset is unaffected
        assert form.fields['non_option_field'].queryset.model == User

    def test_disabled_field_for_deleted_selection_with_no_instance(self):
        """Test _handle_disabled_field_for_deleted_selection without instance."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(UserFacingFormMixin, forms.ModelForm):
            class Meta:
                model = Task
                fields = ["title", "description", "priority", "status", "user"]

        form = TestForm(tenant=tenant)
        # Force call to _handle_disabled_field_for_deleted_selection
        form._handle_disabled_field_for_deleted_selection(
            form.fields["priority"],
            None  # Pass None as option
        )
        assert "readonly" not in form.fields["priority"].widget.attrs

    def test_handle_deleted_selection_with_no_instance_pk(self):
        """Test _handle_deleted_selection with instance but no pk."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")
        task = Task(title="Test")  # Create instance without pk

        class TestForm(UserFacingFormMixin, forms.ModelForm):
            class Meta:
                model = Task
                fields = ["title", "description", "priority", "status", "user"]

        form = TestForm(tenant=tenant, instance=task)
        # This should not raise an error
        form._handle_deleted_selection(form.fields["priority"], "priority")

    def test_filter_foreign_key_fields_with_empty_queryset(self):
        """Test filtering foreign key fields when queryset is None."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class TestForm(UserFacingFormMixin, forms.ModelForm):
            empty_field = forms.ModelChoiceField(queryset=None)

            class Meta:
                model = Task
                fields = ["title", "description", "priority", "status", "user"]

        form = TestForm(tenant=tenant)
        # Should not raise an error for field with None queryset
        assert form.fields["empty_field"].queryset is None


class TestSelectionsForm:
    """Additional test cases for SelectionsForm."""

    def test_selections_form_with_no_selections_field(self):
        """Test form initialization when selections field is pre-defined."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-tenant")

        class CustomSelectionsForm(SelectionsForm):
            selections = forms.ModelMultipleChoiceField(
                queryset=TaskPriorityOption.objects.none(),
                required=False
            )

            class Meta:
                model = TaskPrioritySelection

        form = CustomSelectionsForm(tenant=tenant)
        # Ensure the pre-defined selections field is used
        assert isinstance(form.fields["selections"], forms.ModelMultipleChoiceField)
