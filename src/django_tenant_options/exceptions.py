"""Exceptions for the Django Tenant Options package."""


class ModelClassParsingError(Exception):
    """Used when a model class cannot be parsed from the option provided."""


class IncorrectSubclassError(Exception):
    """Used when the value of `option_model` is not a subclass of the correct abstract model."""


class NoTenantProvidedFromViewError(Exception):
    """Used when a view does not pass an tenant instance from the view to a form."""


class InvalidDefaultOptionError(Exception):
    """Used when a default option defined in a model is not `OptionType.MANDATORY` or `OptionType.OPTIONAL`."""
