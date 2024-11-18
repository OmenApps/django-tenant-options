"""Forms for the Django Tenant Options package."""

import logging

from django import forms
from django.apps import apps
from django.db import IntegrityError
from django.db import transaction
from django.forms.widgets import HiddenInput
from django.utils import timezone

from django_tenant_options.app_settings import DEFAULT_MULTIPLE_CHOICE_FIELD
from django_tenant_options.app_settings import DISABLE_FIELD_FOR_DELETED_SELECTION
from django_tenant_options.choices import OptionType
from django_tenant_options.exceptions import NoTenantProvidedFromViewError
from django_tenant_options.helpers import all_option_subclasses


logger = logging.getLogger("django_tenant_options")


class TenantFormBaseMixin:
    """Base mixin that checks for a valid tenant value passed from the view and hides the tenant field."""

    def __init__(self, *args, **kwargs):
        """Initialize the form with the tenant and hide the tenant field."""
        self.tenant = self._pop_tenant(kwargs)
        super().__init__(*args, **kwargs)
        self._initialize_tenant_field()
        self._remove_associated_tenants_field()

    def _pop_tenant(self, kwargs):
        """Extract and validate the tenant from kwargs."""
        tenant = kwargs.pop("tenant", None)
        if not tenant:
            raise NoTenantProvidedFromViewError("No tenant model class was provided to the form from the view")
        return tenant

    def _initialize_tenant_field(self):
        """Set the tenant field to HiddenInput and initialize it with the tenant instance."""
        if "tenant" in self.fields:
            self.fields["tenant"].initial = self.tenant
            self.fields["tenant"].widget = HiddenInput()

    def _remove_associated_tenants_field(self):
        """Remove the associated_tenants field if it exists."""
        if "associated_tenants" in self.fields:
            del self.fields["associated_tenants"]

    def clean(self):
        """Ensure the tenant is correct even if HiddenField was manipulated."""
        cleaned_data = super().clean()
        cleaned_data["tenant"] = self.tenant
        return cleaned_data


class OptionCreateFormMixin(TenantFormBaseMixin):  # pylint disable=R0903
    """Used in forms that allow a tenant to create a new custom option.

    It requires a `tenant` argument to be passed from the view. This should be an instance of the model
        class provided in the tenant_model parameter of the concrete OptionModel.

    The form will set the option_type field to OptionType.CUSTOM and the tenant field to the tenant instance,
        using a HiddenInput widget.

    Usage:

    .. code-block:: python

        class MyOptionCreateForm(OptionCreateFormMixin, forms.ModelForm):
            class Meta:
                model = MyConcreteOptionModel
                fields = "__all__"


        def my_options_view(request):
            form = MyOptionCreateForm(request.POST, tenant=request.user.tenant)

    """

    def __init__(self, *args, **kwargs):
        """Initialize the form with the tenant and set the option_type field."""
        super().__init__(*args, **kwargs)
        self._initialize_option_type_field()
        self._initialize_deleted_field()

    def _initialize_option_type_field(self):
        """Set the option_type field to OptionType.CUSTOM and use a HiddenInput widget."""
        self.fields["option_type"].widget = HiddenInput()
        self.fields["option_type"].initial = OptionType.CUSTOM

    def _initialize_deleted_field(self):
        """Set the deleted field to None and use a HiddenInput widget."""
        self.fields["deleted"].widget = HiddenInput()
        self.fields["deleted"].initial = None

    def clean(self):
        """Ensure option_type is correct even if HiddenField was manipulated."""
        cleaned_data = super().clean()
        # ensure option_type is correct even if HiddenField was manipulated
        cleaned_data["option_type"] = OptionType.CUSTOM
        return cleaned_data


class OptionUpdateFormMixin(OptionCreateFormMixin):  # pylint disable=R0903
    """Used in forms that allow a tenant to update an existing custom option.

    Has the same operation and requirements as OptionCreateFormMixin, but also allows the option to be deleted.

    Usage:

    .. code-block:: python

        class MyOptionUpdateForm(OptionUpdateFormMixin, forms.ModelForm):
            class Meta:
                model = MyConcreteOptionModel
                fields = "__all__"


        def my_options_view(request, option_id):
            option = MyConcreteOptionModel.objects.get(id=option_id)
            form = MyOptionUpdateForm(request.POST, instance=option, tenant=request.user.tenant)

    """

    def __init__(self, *args, **kwargs):
        """Initialise the form."""
        super().__init__(*args, **kwargs)

        # Add a delete field to the form
        self.fields["delete"] = forms.BooleanField(required=False)

    def clean(self):
        """Clean the form data."""
        cleaned_data = super().clean()

        if cleaned_data.get("delete"):
            cleaned_data["deleted"] = timezone.now()

        return cleaned_data


class SelectionsForm(TenantFormBaseMixin, forms.Form):
    """Creates a form with a `selections` field for managing tenant selections."""

    def __init__(self, *args, **kwargs):
        """Initialize the form with the tenant and set the selections field."""
        self._meta = self.Meta
        self.selection_model = self._meta.model
        self.option_model = apps.get_model(self.selection_model.option_model)
        self.removed_selections = self.option_model.objects.none()
        self.multiple_choice_field_class = DEFAULT_MULTIPLE_CHOICE_FIELD
        super().__init__(*args, **kwargs)
        self._initialize_selections_field()
        self._remove_option_field()
        self._set_selections_queryset()

    def _initialize_selections_field(self):
        """Initialize the `selections` field if it's not already present."""
        if "selections" not in self.fields:
            self.fields["selections"] = self.multiple_choice_field_class(
                queryset=self.option_model.objects.none(), required=False
            )

    def _remove_option_field(self):
        """Remove the `option` field if it exists."""
        if "option" in self.fields:
            del self.fields["option"]

    def _set_selections_queryset(self):
        """Set the queryset for the `selections` field based on the tenant."""
        self.fields["selections"].queryset = self.selection_model.objects.options_for_tenant(self.tenant)
        self.fields["selections"].initial = self.selection_model.objects.selected_options_for_tenant(self.tenant)

    def clean(self):
        """Ensure `selections` include mandatory options and identify removed selections."""
        cleaned_data = super().clean()
        cleaned_data["selections"] = self._combine_selections_and_mandatory(cleaned_data.get("selections", []))
        self.removed_selections = self._identify_removed_selections(cleaned_data["selections"])
        logger.debug("cleaned_data: %s", cleaned_data)
        return cleaned_data

    def _combine_selections_and_mandatory(self, selections):
        """Combine the selections with mandatory options."""
        if selections is None:
            selections = self.option_model.objects.none()
        mandatory_options = self.option_model.objects.filter(option_type=OptionType.MANDATORY)
        return (selections | mandatory_options).distinct()

    def _identify_removed_selections(self, selections):
        """Identify options removed from the selection by the user."""
        current_selections = self.selection_model.objects.filter(tenant=self.tenant, deleted__isnull=True).values_list(
            "option_id", flat=True
        )

        # Exclude mandatory options and get currently selected options that aren't in the new selections
        return self.option_model.objects.filter(
            id__in=current_selections, option_type__in=[OptionType.OPTIONAL, OptionType.CUSTOM]
        ).exclude(id__in=selections.values_list("id", flat=True))

    def save(self, *args, **kwargs):
        """Save the selections to the database, handling added and removed options."""
        try:
            with transaction.atomic():
                self._delete_removed_selections()
                self._save_new_selections()
        except IntegrityError as e:
            logger.warning("Problem creating or deleting selections for %s: %s", self.tenant, e)
        super().__init__(*args, **kwargs, tenant=self.tenant)

    def _delete_removed_selections(self):
        """Delete any selections that were removed."""
        self.selection_model.objects.filter(
            tenant=self.tenant, option__in=self.removed_selections, deleted__isnull=True
        ).update(deleted=timezone.now())

    def _save_new_selections(self):
        """Create or update the selections that were added."""
        for selection in self.cleaned_data["selections"]:
            self.selection_model.objects.update_or_create(
                tenant=self.tenant, option=selection, defaults={"deleted": None}
            )


class UserFacingFormMixin:
    """Mixin to handle user-facing forms with Options fields."""

    def __init__(self, *args, **kwargs):
        """Initialize the form with the tenant and filter ForeignKey fields related to AbstractOption subclasses."""
        self.tenant = kwargs.pop("tenant", None)
        if not self.tenant:
            raise NoTenantProvidedFromViewError("No tenant model class was provided to the form from the view")
        super().__init__(*args, **kwargs)
        self._initialize_tenant_field()
        self._remove_associated_tenants_field()
        self._filter_foreign_key_fields()

    def _initialize_tenant_field(self):
        """Initialize the `tenant` field with the tenant instance and set it to `HiddenInput`."""
        if "tenant" in self.fields:
            self.fields["tenant"].initial = self.tenant
            self.fields["tenant"].widget = HiddenInput()

    def _remove_associated_tenants_field(self):
        """Remove the `associated_tenants` field if it exists."""
        if "associated_tenants" in self.fields:
            del self.fields["associated_tenants"]

    def _filter_foreign_key_fields(self):
        """Filter queryset for ForeignKey fields related to AbstractOption subclasses."""
        option_subclasses = all_option_subclasses()
        for field_name, field in self.fields.items():
            if self._is_foreign_key_to_option_subclass(field, option_subclasses):
                logger.debug("field_name: %s for field: %s", field_name, field)
                self._filter_queryset_for_tenant(field)
                self._set_field_initial_value(field_name)
                self._handle_deleted_selection(field, field_name)

    def _is_foreign_key_to_option_subclass(self, field, option_subclasses):
        """Check if the field is a ForeignKey to an AbstractOption subclass."""
        return (
            isinstance(field, forms.ModelChoiceField)
            and field.queryset is not None
            and field.queryset.model in option_subclasses
        )

    def _filter_queryset_for_tenant(self, field):
        """Filter the queryset to only show options selected for the tenant."""
        field.queryset = field.queryset.model.objects.selected_options_for_tenant(self.tenant)

    def _set_field_initial_value(self, field_name):
        """Set the initial value for the field if there's an instance."""
        if hasattr(self, "instance") and hasattr(self.instance, "pk") and self.instance.pk:
            field_value = getattr(self.instance, field_name)
            if field_value:
                self.fields[field_name].initial = field_value.pk

    def _handle_deleted_selection(self, field, field_name):
        """Handle the case where a selection has been deleted."""
        if hasattr(self, "instance") and hasattr(self.instance, "pk") and self.instance.pk:
            option_for_this_field = getattr(self.instance, field_name)
            if option_for_this_field and option_for_this_field not in field.queryset:
                self._handle_disabled_field_for_deleted_selection(field, option_for_this_field)

    def _handle_disabled_field_for_deleted_selection(self, field, option_for_this_field):
        """Disable the field if the selected option has been deleted and setting is enabled."""
        if DISABLE_FIELD_FOR_DELETED_SELECTION and option_for_this_field.pk:
            field.queryset = field.queryset | field.queryset.model.objects.filter(pk=option_for_this_field.pk)
            field.widget.attrs["readonly"] = "readonly"
            field.widget.attrs["disabled"] = "disabled"

    def clean(self):
        """Ensure the tenant is correct even if HiddenField was manipulated."""
        cleaned_data = super().clean()
        cleaned_data["tenant"] = self.tenant
        return cleaned_data
