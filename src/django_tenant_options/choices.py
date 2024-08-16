"""Choices for the OptionType model field."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class OptionType(models.TextChoices):
    """Allowable Options Types."""

    MANDATORY = "dm", _("Default Mandatory")  # Tenant can see, but not change this option
    OPTIONAL = "do", _("Default Optional")  # Tenant can see and select/unselect this option
    CUSTOM = "cu", _("Custom")  # Tenant created this option and can select/unselect it
