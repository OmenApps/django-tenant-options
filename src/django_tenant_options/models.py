"""Models for the Django Tenant Options app."""

import logging

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django.db.models.constraints import CheckConstraint
from django.db.models.constraints import UniqueConstraint
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_tenant_options import is_installed_less_than_version
from django_tenant_options.app_settings import ASSOCIATED_TENANTS_RELATED_NAME
from django_tenant_options.app_settings import ASSOCIATED_TENANTS_RELATED_QUERY_NAME
from django_tenant_options.app_settings import OPTION_MODEL_RELATED_NAME
from django_tenant_options.app_settings import OPTION_MODEL_RELATED_QUERY_NAME
from django_tenant_options.app_settings import OPTION_ON_DELETE
from django_tenant_options.app_settings import TENANT_MODEL
from django_tenant_options.app_settings import TENANT_MODEL_RELATED_NAME
from django_tenant_options.app_settings import TENANT_MODEL_RELATED_QUERY_NAME
from django_tenant_options.app_settings import TENANT_ON_DELETE
from django_tenant_options.choices import OptionType
from django_tenant_options.exceptions import IncorrectSubclassError
from django_tenant_options.exceptions import InvalidDefaultOptionError


logger = logging.getLogger("django_tenant_options")


def validate_model_is_concrete(model):
    """Raises an error if the provided model class is abstract."""
    if model._meta.abstract:  # pylint: disable=W0212
        raise IncorrectSubclassError(f"Model {model.__name__} is abstract.")


def validate_model_has_attribute(model, attr: str, attr_type=None):
    """Raises an error if the provided model class does not contain the specified attribute with correct type.

    If `attr_type` is not specified, the function only checks that the attribute is present.
    """
    if hasattr(model, attr):
        if attr_type is not None and not isinstance(getattr(model, attr), attr_type):
            raise AttributeError(f"Model {model.__name__} has incorrect type for attribute {attr}.")
    else:
        raise AttributeError(f"Model {model.__name__} is missing attribute {attr}.")


class TenantOptionsCoreModelBase(ModelBase):
    """Base Metaclass for providing ForeignKey to a tenant model in other metaclasses."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Add ForeignKey to the tenant model class."""
        model = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in bases:
            if base.__name__ in ["AbstractSelection", "AbstractOption"]:
                ConcreteModel = model  # pylint: disable=C0103

                validate_model_has_attribute(ConcreteModel, "tenant_model")
                validate_model_has_attribute(ConcreteModel, "tenant_on_delete")

                validate_model_is_concrete(ConcreteModel)

                fields = {
                    "on_delete": ConcreteModel.tenant_on_delete,
                    "related_name": ConcreteModel.tenant_model_related_name,
                    "related_query_name": ConcreteModel.tenant_model_related_query_name,
                }

                # If the model is AbstractOption, allow the ForeignKey to be blank and null.
                #   This is because the tenant is not used for MANDATORY or OPTIONAL Options
                #   but is needed for CUSTOM Options and is required for all Selections.
                if base.__name__ == "AbstractOption":
                    fields["blank"] = True
                    fields["null"] = True

                ConcreteModel.add_to_class("tenant", models.ForeignKey(ConcreteModel.tenant_model, **fields))

        return model


class OptionModelBase(TenantOptionsCoreModelBase):
    """Metaclass for defining the default options available to all tenants.

    Extends TenantOptionsCoreModelBase, which provides a ForeignKey to the tenant model in model metaclasses.

    Used to add a ManyToManyField from concrete classes of AbstractOption the Tenant model, through a concrete class
        of AbstractSelection.

    Within the model, set the `selection_model` parameter to the concrete class inheriting AbstractSelection
      and `tenant_model` to the tenant model to be used for both concrete classes.

    For instance:

    .. code-block:: python

        class ConcreteOption(AbstractOption):
            tenant_model = "myapp.Tenant"
            selection_model = "myapp.ConcreteSelection"
    """

    def __new__(cls, name, bases, attrs, **kwargs):
        """Add ManyToManyField to the model class."""
        model = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in bases:
            if base.__name__ == "AbstractOption":
                ConcreteOptionModel = model  # pylint: disable=C0103

                validate_model_has_attribute(ConcreteOptionModel, "tenant_model")
                validate_model_has_attribute(ConcreteOptionModel, "selection_model")

                validate_model_is_concrete(ConcreteOptionModel)

                ConcreteOptionModel.add_to_class(
                    "associated_tenants",
                    models.ManyToManyField(
                        ConcreteOptionModel.tenant_model,
                        through=ConcreteOptionModel.selection_model,
                        through_fields=("option", "tenant"),
                        related_name=ConcreteOptionModel.associated_tenants_related_name,  # "selected"
                        related_query_name=ConcreteOptionModel.associated_tenants_related_query_name,
                    ),
                )

        return model


class SelectionModelBase(TenantOptionsCoreModelBase):
    """Metaclass for defining which options have been selected for a given tenant.

    Extends TenantOptionsCoreModelBase, which provides a ForeignKey to the tenant model in model metaclasses.

    Used to set up the ManyToManyField from concrete classes of AbstractSelection
        to concrete classes of AbstractOption.

    Within the model, set the `option_model` parameter to the concrete class inheriting AbstractOption
      and `tenant_model` to the model tenant which is associated with both concrete classes.

    For instance:

    .. code-block:: python

        class ConcreteSelection(AbstractSelection):
            tenant_model = "myapp.Tenant"
            option_model = "myapp.ConcreteOption"
    """

    def __new__(cls, name, bases, attrs, **kwargs):
        """Adds ForeignKey to the model class."""
        model = super().__new__(cls, name, bases, attrs, **kwargs)

        for base in bases:
            if base.__name__ == "AbstractSelection":
                ConcreteSelectionModel = model  # pylint: disable=C0103

                validate_model_has_attribute(ConcreteSelectionModel, "option_model")
                validate_model_has_attribute(ConcreteSelectionModel, "option_on_delete")

                validate_model_is_concrete(ConcreteSelectionModel)

                ConcreteSelectionModel.add_to_class(
                    "option",
                    models.ForeignKey(
                        ConcreteSelectionModel.option_model,
                        on_delete=ConcreteSelectionModel.option_on_delete,
                        related_name=ConcreteSelectionModel.option_model_related_name,
                        related_query_name=ConcreteSelectionModel.option_model_related_query_name,
                        blank=True,
                        null=True,
                    ),
                )

        return model


class OptionQuerySet(models.QuerySet):
    """Custom QuerySet for Option models.

    Subclass this QuerySet to provide additional functionality for your concrete Option model.
    """

    def active(self):
        """Return only active options."""
        return self.filter(deleted__isnull=True)

    def deleted(self):
        """Return only deleted options."""
        return self.filter(deleted__isnull=False)

    def custom_options(self):
        """Return only custom options."""
        return self.filter(option_type=OptionType.CUSTOM)

    def options_for_tenant(self, tenant, include_deleted=False) -> models.QuerySet:
        """Returns all available options for a given tenant, as below.

        - all required default options
        - all non-required default options
        - all tenant-specific options for this tenant

        Set `include_deleted=True` to include deleted options.
        """
        base_query = (
            Q(option_type=OptionType.MANDATORY)
            | Q(option_type=OptionType.OPTIONAL)
            | Q(option_type=OptionType.CUSTOM, tenant=tenant)
        )

        if include_deleted:
            return self.filter(base_query)
        return self.active().filter(base_query)

    def selected_options_for_tenant(self, tenant, include_deleted=False) -> models.QuerySet:
        """Returns a QuerySet of the AbstractOption subclassed model.

        Includes all *selected* options for a given tenant, including:

        - all mandatory default options
        - all selected optional default options for this tenant
        - all selected custom options for this tenant

        Set `include_deleted=True` to include deleted options.
        """
        logger.debug("Called selected_options_for_tenant in OptionQuerySet with %s, %s", tenant, include_deleted)

        try:
            SelectionModel = self.model.associated_tenants.through
            selections = SelectionModel.objects.active().filter(tenant=tenant).values_list("option", flat=True)

            base_query = Q(option_type=OptionType.MANDATORY) | (
                Q(id__in=selections)
                & (Q(option_type=OptionType.OPTIONAL) | Q(option_type=OptionType.CUSTOM, tenant=tenant))
            )

            if include_deleted:
                return self.filter(base_query)
            return self.active().filter(base_query)

        except LookupError:
            return self.none()

    def undelete(self):
        """Update all records in the current QuerySet to remove the deleted timestamp."""
        return self.update(deleted=None)

    def delete(self, override=False):
        """Delete the records in the current QuerySet.

        Args:
            override: If True, perform a hard delete. Otherwise, perform a soft delete.
        """
        if override:
            return super().delete()
        return self.update(deleted=timezone.now())


class OptionManager(models.Manager):
    """Manager for Option models.

    Provides methods for creating default options and filtering out deleted options.

    Subclass this manager to provide additional functionality for your concrete Option model.
    """

    def create_for_tenant(self, tenant, name: str):
        """Provided a tenant and a option name, creates the new option for that tenant."""
        return self.create(tenant=tenant, name=name, option_type=OptionType.CUSTOM)

    def create_mandatory(self, name: str):
        """Provided an option name, creates the new option (mandatorily selected for all tenants)."""
        return self.create(name=name, option_type=OptionType.MANDATORY)

    def create_optional(self, name: str):
        """Provided an option name, creates the new optional option (selectable by all tenants)."""
        return self.create(name=name, option_type=OptionType.OPTIONAL)

    def _update_or_create_default_option(self, item_name: str, options_dict: dict = dict):
        """Updates or creates a single default Mandatory or Optional option.

        Requires a name and options_dict, which may contain the following keys:
        - option_type: OptionType.MANDATORY or OptionType.OPTIONAL

        This method can be overridden in subclassed Manager to modify how concrete instances are created, but
          this should not be necessary.
        """
        # Default to MANDATORY option type
        option_type = OptionType.MANDATORY

        # If option_type key is present in the options_dict, validate that it is MANDATORY or OPTIONAL
        #   Note: CUSTOM option types cannot be defined as a default option
        for key, value in options_dict.items():
            if key == "option_type":
                option_type = value  # Set the option_type variable to the value provided
                if option_type not in [OptionType.MANDATORY, OptionType.OPTIONAL]:
                    raise InvalidDefaultOptionError(
                        f"Option defaults must be of type `OptionType.MANDATORY` or `OptionType.OPTIONAL`. "
                        f"You specified {key} = {value} for {item_name=}."
                    )

        obj, created = self.model.objects.update_or_create(
            name=item_name,
            option_type=option_type,
            defaults={"deleted": None},  # Undelete the option if it was previously deleted
        )

    def _update_default_options(self) -> dict:
        """Import default options, and soft-delete MANDATORY & OPTIONAL options that are no longer in the default list.

        Steps:
        - Get the default options from `Model.default_options`
        - Create instances if they do not already exist or update if options have changed
        - Soft-delete options that are no longer in the default list by setting `deleted` to the current time
        - Add the `deleted` key to the default options dict

        Example:
        .. code-block:: python

            default_options = {
                "Cereal and Grass": {"option_type": OptionType.MANDATORY},               # Creates a mandatory instance
                "Cereal and Grass - Alfalfa_Hay": {},                                     # Creates a mandatory instance
                "Cereal and Grass - Alfalfa_Seed": {"option_type": OptionType.OPTIONAL},  # Creates an optional instance
            }

        Note, it is not necessary to specify `{"option_type": OptionType.MANDATORY}` since options are
        mandatory by default. You could set the dict to `{}` and the value model instance will be
        set to mandatory.
        """
        validate_model_is_concrete(self.model)

        updated_options = {}
        default_options = getattr(self.model, "default_options", {})

        # Create or update default options
        for name, options_dict in default_options.items():
            try:
                self.model.objects._update_or_create_default_option(name, options_dict)
                updated_options[name] = options_dict
            except Exception as e:
                logger.error(f"Error updating option {name}: {e}")

        # Soft delete options no longer in defaults
        existing_options = self.model.objects.filter(
            option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL], deleted__isnull=True
        ).exclude(name__in=default_options.keys())

        for option in existing_options:
            option.delete()
            updated_options[option.name] = {"deleted": True}

        return updated_options


def get_constraint_dict():
    """Return the constraint dictionary for the CheckConstraint in AbstractOption."""

    def get_condition_argument_name():
        """Get the name of the argument to pass to the CheckConstraint.

        In Django 5.1.0, the argument name is changed from `check` to `condition`.
        """
        if is_installed_less_than_version("5.1.0"):
            return "check"
        return "condition"

    # Options of type OptionType.CUSTOM must have a specified tenant, and Options of
    # type OptionType.MANDATORY and OptionType.OPTIONAL must not have a specified tenant
    return {
        get_condition_argument_name(): Q(option_type=OptionType.CUSTOM, tenant__isnull=False)
        | Q(option_type=OptionType.MANDATORY, tenant__isnull=True)
        | Q(option_type=OptionType.OPTIONAL, tenant__isnull=True),
        "name": "%(app_label)s_%(class)s_tenant_check",
    }


class AbstractOption(models.Model, metaclass=OptionModelBase):
    """Abstract model for defining all available Options.

    Options which are provided by default through model configuration may be Mandatory or Optional.

    Using `instance.delete()` only soft-deletes the option.
    """

    default_options = {}

    tenant_model = TENANT_MODEL
    tenant_on_delete = TENANT_ON_DELETE
    tenant_model_related_name = TENANT_MODEL_RELATED_NAME
    tenant_model_related_query_name = TENANT_MODEL_RELATED_QUERY_NAME

    selection_model = None

    associated_tenants_related_name = ASSOCIATED_TENANTS_RELATED_NAME
    associated_tenants_related_query_name = ASSOCIATED_TENANTS_RELATED_QUERY_NAME

    option_type = models.CharField(
        _("Option Type"),
        choices=OptionType.choices,
        default=OptionType.OPTIONAL,
        max_length=3,
        blank=True,
    )

    name = models.CharField(_("Option Name"), max_length=100)
    deleted = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When was this option deleted?"),
    )

    objects = OptionManager.from_queryset(OptionQuerySet)()
    unscoped = models.Manager()

    class Meta:  # pylint: disable=R0903
        """Meta options for AbstractOption.

        Subclass this in your concrete model's Meta class to enforce constraints on the model.
        """

        verbose_name = _("Option")
        verbose_name_plural = _("Options")

        constraints = [
            # A tenant cannot have more than one option with the same name
            UniqueConstraint(
                Lower("name"),
                "tenant",
                name="%(app_label)s_%(class)s_unique_name",
            ),
            CheckConstraint(**get_constraint_dict()),
        ]
        abstract = True

    def delete(self, using=None, keep_parents=False, override=False):
        """Delete the option, with option for hard delete.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent models
            override: If True, perform a hard delete. Otherwise, perform a soft delete.
        """
        if override:
            # Update related selections
            selection_model_class = apps.get_model(self.selection_model)
            selection_model_class.objects.filter(option=self).update(deleted=timezone.now())
            # Hard delete
            result = super().delete(using=using, keep_parents=keep_parents)
            return result

        # Soft delete
        self.deleted = timezone.now()
        self.save()

    def __str__(self):
        """Return the name of the option."""
        return self.name

    @classmethod
    def get_concrete_subclasses(cls) -> list:
        """Return a list of model classes which are subclassed from AbstractOption.

        Only include those models that are not themselves Abstract.
        """
        result = []
        for model in apps.get_models():
            if issubclass(model, cls) and model is not cls and not model._meta.abstract:  # pylint: disable=W0212
                result.append(model)
        return result

    def clean(self):
        """Ensure no tenant can have the same name as a MANDATORY or OPTIONAL option."""
        if self.option_type == OptionType.CUSTOM:
            conflicting_options = type(self).objects.filter(
                name=self.name, option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL]
            )
            if conflicting_options.exists():
                raise ValidationError(
                    {"name": _("A custom option cannot have the same name as a mandatory or optional option.")}
                )

        super().clean()

    def save(self, *args, **kwargs):
        """Ensure that the option is valid before saving."""
        self.clean()
        super().save(*args, **kwargs)


class SelectionQuerySet(models.QuerySet):
    """Custom QuerySet for Selection models.

    Subclass this QuerySet to provide additional functionality for your concrete Selection model.
    """

    def active(self):
        """Return only active selections."""
        return self.filter(deleted__isnull=True)

    def deleted(self):
        """Return only deleted selections."""
        return self.filter(deleted__isnull=False)

    def undelete(self):
        """Update all records in the current QuerySet to remove deleted timestamp."""
        return self.update(deleted=None)

    def delete(self, override=False):
        """Delete the records in the current QuerySet.

        Args:
            override: If True, perform a hard delete. Otherwise, perform a soft delete.
        """
        if override:
            return super().delete()
        return self.update(deleted=timezone.now())


class SelectionManager(models.Manager):
    """Custom Manager for Selection models.

    Subclass this manager to provide additional functionality for your concrete Selection model.
    """

    def options_for_tenant(self, tenant, include_deleted=False):
        """Returns a QuerySet of the AbstractOption subclassed model.

        Includes all *available* options for a given tenant, including:

        - all required default options
        - all non-required default options
        - all tenant-specific options

        Set `include_deleted=True` to include deleted options.
        """
        try:
            OptionsModel = apps.get_model(self.model.option_model)  # pylint: disable=C0103
            return OptionsModel.objects.options_for_tenant(tenant=tenant, include_deleted=include_deleted)
        except LookupError as e:
            # no such model in this application
            logger.warning(e)
            return None

    def selected_options_for_tenant(self, tenant, include_deleted=False):
        """Returns a QuerySet of the AbstractOption subclassed model.

        Includes all *selected* options for a given tenant, including:

        - all mandatory default options
        - all selected optional default options for this tenant
        - all selected custom options for this tenant

        Set `include_deleted=True` to include deleted options.
        """
        logger.debug("Called selected_options_for_tenant in SelectionManager with %s, %s", tenant, include_deleted)
        try:
            OptionsModel = apps.get_model(self.model.option_model)  # pylint: disable=C0103
            return OptionsModel.objects.selected_options_for_tenant(tenant=tenant, include_deleted=include_deleted)
        except LookupError as e:
            # no such model in this application
            logger.warning(e)
            return None


class AbstractSelection(models.Model, metaclass=SelectionModelBase):
    """Identifies all selected Options for a given tenant, which it's users can then choose from.

    A single tenant can select multiple Options. This model is a through model for the ManyToManyField
        between the Tenant and the Option.
    """

    tenant_model = TENANT_MODEL
    tenant_on_delete = TENANT_ON_DELETE
    tenant_model_related_name = TENANT_MODEL_RELATED_NAME
    tenant_model_related_query_name = TENANT_MODEL_RELATED_QUERY_NAME

    option_model = None
    option_on_delete = OPTION_ON_DELETE
    option_model_related_name = OPTION_MODEL_RELATED_NAME
    option_model_related_query_name = OPTION_MODEL_RELATED_QUERY_NAME

    deleted = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When was this selection deleted?"),
    )

    objects = SelectionManager.from_queryset(SelectionQuerySet)()
    unscoped = models.Manager()

    class Meta:  # pylint: disable=R0903
        """Meta options for AbstractSelection.

        Subclass this in your concrete model's Meta class to enforce constraints on the model.
        """

        verbose_name = _("Selection")
        verbose_name_plural = _("Selections")
        constraints = [
            UniqueConstraint(
                "tenant",
                "option",
                name="%(app_label)s_%(class)s_name_val",
            ),
        ]
        abstract = True

    def clean(self):
        """Ensure that the selected option is available to the tenant."""
        if self.option.tenant and self.option.tenant != self.tenant:  # pylint: disable=E1101
            raise ValueError(
                "The selected custom option '%s' belongs to tenant '%s', and is not available to tenant '%s'."
                % (self.option.name, self.option.tenant, self.tenant)
            )

        super().clean()

    def save(self, *args, **kwargs):
        """Ensure that the selection is valid before saving."""
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False, override=False):
        """Delete the selection, with option for hard delete.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent models
            override: If True, perform a hard delete. Otherwise, perform a soft delete
        """
        if override:
            return super().delete(using=using, keep_parents=keep_parents)
        else:
            self.deleted = timezone.now()
            self.save()

    @classmethod
    def get_concrete_subclasses(cls) -> list:
        """Return a list of model classes which are subclassed from AbstractSelection.

        Only include those models that are not themselves Abstract.
        """
        result = []
        for model in apps.get_models():
            if issubclass(model, cls) and model is not cls and not model._meta.abstract:  # pylint: disable=W0212
                result.append(model)
        return result
