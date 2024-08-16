"""Custom form fields for the django_tenant_options app."""

import logging

from django import forms

from django_tenant_options.choices import OptionType


logger = logging.getLogger("django_tenant_options")


class OptionsModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Displays objects and shows which are mandatory."""

    def label_from_instance(self, obj):
        """Return a label for each object."""
        labels = {
            OptionType.MANDATORY: f"{obj.name} (mandatory)",
            OptionType.OPTIONAL: f"{obj.name} (optional)",
            OptionType.CUSTOM: f"{obj.name} (custom)",
        }

        return labels.get(obj.option_type, obj.name)
