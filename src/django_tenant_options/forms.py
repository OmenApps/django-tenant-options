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


class TenantFormBaseMixin:  # pylint disable=R0903
    """Checks that we have a valid tenant value passed in from the view, and hides the tenant field."""

    def __init__(self, *args, **kwargs):
        """Initialise the form."""
        self.tenant = kwargs.pop("tenant", None)
        if not self.tenant:
            raise NoTenantProvidedFromViewError("No tenant model class was provided to the form from the view")
        super().__init__(*args, **kwargs)

        # Ensure that the 'tenant' field is available and then set it to HiddenInput
        if "tenant" in self.fields:
            self.fields["tenant"].initial = self.tenant
            self.fields["tenant"].widget = HiddenInput()

        # Remove the associated_tenants field if it exists
        if "associated_tenants" in self.fields:
            del self.fields["associated_tenants"]

    def clean(self):
        """Clean the form data."""
        cleaned_data = super().clean()

        # ensure tenant is correct even if HiddenField was manipulated
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
        """Initialise the form."""
        super().__init__(*args, **kwargs)

        # Set the option_type field value to OptionType.CUSTOM and use a HiddenInput widget
        self.fields["option_type"].widget = HiddenInput()
        self.fields["option_type"].initial = OptionType.CUSTOM

        # Set the deleted field value to None and use a HiddenInput widget
        self.fields["deleted"].widget = HiddenInput()
        self.fields["deleted"].initial = None

    def clean(self):
        """Clean the form data."""
        cleaned_data = super().clean()

        # ensure option_type is correct even if HiddenField was manipulated
        cleaned_data["option_type"] = OptionType.CUSTOM
        return cleaned_data


class OptionUpdateFormMixin(OptionCreateFormMixin):  # pylint disable=R0903
    """Used in forms that allow a tenant to update an existing option.

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
    """Creates a form with a `selections` field, defaulting to OptionsModelMultipleChoiceField.

    Usage:

    .. code-block:: python

        class MyModelForm(SelectionsModelForm):
            class Meta:
                model = TenantCropSelection

        def my_selections_view(request):
            form = MyModelForm(request.POST, tenant=request.user.tenant)

    """

    def __init__(self, *args, **kwargs):
        """Initialise the form."""
        self._meta = self.Meta
        self.selection_model = self._meta.model
        self.option_model = apps.get_model(self.selection_model.option_model)
        self.removed_selections = self.option_model.objects.none()
        self.multiple_choice_field_class = OptionsModelMultipleChoiceField  # ToDo: Add docs for this
        super().__init__(*args, **kwargs)
        if not "selections" in self.fields:
            self.fields["selections"] = self.multiple_choice_field_class(
                queryset=self.option_model.objects.none(), required=False
            )
        if "option" in self.fields:
            del self.fields["option"]

        # Get all allowed options for this tenant
        self.fields["selections"].queryset = self.selection_model.objects.options_for_tenant(self.tenant)

        # Make sure the current selections (and mandatory options) are selected in the form
        self.fields["selections"].initial = self.selection_model.objects.selected_options_for_tenant(self.tenant)

    def clean(self):
        """Ensure option_type and selections contain mandatory items even if HiddenField was manipulated."""
        cleaned_data = super().clean()

        # Combine the distinct set of returned selections and mandatory options
        cleaned_selections = (
            cleaned_data["selections"] | self.option_model.objects.filter(option_type=OptionType.MANDATORY)
        ).distinct()

        # Identify which options were removed from selection by removing the selected and MANDATORY options
        self.removed_selections = self.option_model.objects.exclude(id__in=cleaned_selections).exclude(
            option_type=OptionType.MANDATORY
        )

        cleaned_data["selections"] = cleaned_selections
        logger.debug("cleaned_data: %s", cleaned_data)

        return cleaned_data

    def save(self, *args, **kwargs):
        """Save the selections to the database."""
        try:
            with transaction.atomic():
                # Delete any selections that were removed
                self.selection_model.objects.filter(option__in=self.removed_selections).delete()
                # Create or update the selections that were added
                for selection in self.cleaned_data["selections"]:
                    self.selection_model.objects.update_or_create(
                        tenant=self.tenant, option=selection, defaults={"deleted": None}
                    )
        except IntegrityError as e:
            logger.warning("Problem creating or deleting selections for %s: %s", self.tenant, e)
        super().__init__(*args, **kwargs, tenant=self.tenant)
