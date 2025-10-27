"""Models for the Django Tenant Options app."""

import logging
import traceback

from django.apps import apps
from django.core.checks import Error
from django.core.checks import Warning
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Manager
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
from django_tenant_options.app_settings import model_config
from django_tenant_options.choices import OptionType
from django_tenant_options.exceptions import IncorrectSubclassError
from django_tenant_options.exceptions import InvalidDefaultOptionError
from django_tenant_options.exceptions import ModelValidationError

from .checks import check_manager_compliance


logger = logging.getLogger("django_tenant_options")


def validate_model_relationship(model_class, field_name, related_model):
    """Validate model relationships with detailed error messages."""
    try:
        if not hasattr(model_class, field_name):
            raise ModelValidationError(
                f"Missing required field '{field_name}' on {model_class.__name__}"
            )

        field = getattr(model_class, field_name)

        logger.debug(
            "Validating relationship: %s.%s (%s)",
            model_class.__name__,
            field_name,
            type(field),
        )

        # Special handling for model reference strings (e.g. 'app.Model')
        if field_name.endswith("_model"):
            if not isinstance(field, str):
                raise ModelValidationError(
                    f"Invalid type for '{field_name}' on {model_class.__name__}. "
                    f"Expected string (e.g. 'app.Model'), got {type(field).__name__}"
                )
            if "." not in field:
                raise ModelValidationError(
                    f"Invalid format for '{field_name}' on {model_class.__name__}. "
                    f"Expected 'app.Model' format, got '{field}'"
                )
        # Special handling for on_delete fields
        elif field_name.endswith("_on_delete"):
            if field not in [
                models.CASCADE,
                models.PROTECT,
                models.SET_NULL,
                models.SET_DEFAULT,
                models.SET,
                models.DO_NOTHING,
            ]:
                raise ModelValidationError(
                    f"Invalid on_delete value for '{field_name}' on {model_class.__name__}. "
                    f"Expected a valid on_delete function (e.g. models.CASCADE)"
                )
        # Special handling for relationship fields that become descriptors
        elif field_name in ["tenant", "option"]:
            if not (
                hasattr(field, "field") and isinstance(field.field, models.ForeignKey)
            ):
                raise ModelValidationError(
                    f"Invalid relationship field '{field_name}' on {model_class.__name__}. "
                    f"Expected ForeignKey relationship"
                )
        elif field_name == "associated_tenants":
            if not (
                hasattr(field, "field")
                and isinstance(field.field, models.ManyToManyField)
            ):
                raise ModelValidationError(
                    f"Invalid relationship field '{field_name}' on {model_class.__name__}. "
                    f"Expected ManyToManyField relationship"
                )
        else:
            if not isinstance(field, related_model) and not issubclass(
                type(field), related_model
            ):
                raise ModelValidationError(
                    f"Invalid type for '{field_name}' on {model_class.__name__}. "
                    f"Expected {related_model.__name__}, got {type(field).__name__}"
                )

        logger.debug(
            "Successfully validated relationship %s on %s (type: %s)",
            field_name,
            model_class.__name__,
            type(field).__name__,
        )

    except Exception as e:
        logger.error(
            "Failed to validate model relationship: %s\n%s",
            str(e),
            traceback.format_exc(),
        )
        raise


def get_all_managers(model):
    """Get all managers from a model using multiple approaches."""
    managers = set()

    # Check default manager
    if hasattr(model._meta, "default_manager"):
        managers.add(model._meta.default_manager)

    # Check _managers list
    if hasattr(model._meta, "_managers"):
        managers.update(model._meta._managers)

    # Check direct manager attributes
    for attr_name in dir(model):
        attr = getattr(model, attr_name)
        if isinstance(attr, Manager) and attr.__class__ != Manager:
            managers.add(attr)

    return managers


def validate_model_is_concrete(model):
    """Raises an error if the provided model class is abstract."""
    try:
        if model._meta.abstract:
            raise IncorrectSubclassError(f"Model {model.__name__} is abstract.")
    except IncorrectSubclassError as exc:
        logger.exception("validate_model_is_concrete error: %s", exc)
        raise


def validate_model_has_attribute(model, attr: str, attr_type=None):
    """Raises an error if the provided model class does not contain the specified attribute with correct type.

    If `attr_type` is not specified, the function only checks that the attribute is present.
    """
    try:
        if not hasattr(model, attr):
            raise AttributeError(f"Model {model.__name__} is missing attribute {attr}.")
        if attr_type and not isinstance(getattr(model, attr), attr_type):
            raise AttributeError(
                f"Model {model.__name__} has incorrect type for attribute {attr}."
            )
    except AttributeError as exc:
        logger.exception("validate_model_has_attribute error: %s", exc)
        raise


class TenantOptionsCoreModelBase(ModelBase):
    """Base Metaclass for providing ForeignKey to a tenant model in other metaclasses."""

    def __new__(cls, name, bases, attrs, **kwargs):
        """Add ForeignKey to the tenant model class."""
        model = None
        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)
            for base in bases:
                if base.__name__ in ["AbstractSelection", "AbstractOption"]:
                    ConcreteModel = model  # pylint: disable=C0103

                    validate_model_has_attribute(ConcreteModel, "tenant_model")
                    validate_model_has_attribute(ConcreteModel, "tenant_on_delete")

                    validate_model_relationship(ConcreteModel, "tenant_model", str)
                    validate_model_relationship(
                        ConcreteModel, "tenant_on_delete", models.Field
                    )

                    validate_model_is_concrete(ConcreteModel)

                    # Check if 'tenant' field already exists to prevent duplicate field creation
                    # Critical for PostgreSQL tests where metaclasses can run multiple times
                    if not hasattr(ConcreteModel, "tenant") or "tenant" not in [
                        f.name for f in ConcreteModel._meta.get_fields()
                    ]:
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

                        ConcreteModel.add_to_class(
                            "tenant",
                            model_config.foreignkey_class(
                                ConcreteModel.tenant_model, **fields
                            ),
                        )

                        # Validate the tenant field after it's been added
                        logger.debug(
                            "Validating tenant field after adding it to %s", name
                        )
                        validate_model_relationship(
                            ConcreteModel, "tenant", model_config.foreignkey_class
                        )
                    else:
                        logger.debug(
                            "Field 'tenant' already exists on %s, skipping add_to_class",
                            name,
                        )

        except Exception as e:
            logger.exception(
                "Error creating model %s in TenantOptionsCoreModelBase: %s", name, e
            )
            raise
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
        model = None

        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)
            for base in bases:
                if base.__name__ == "AbstractOption":
                    ConcreteOptionModel = model  # pylint: disable=C0103

                    validate_model_has_attribute(ConcreteOptionModel, "tenant_model")
                    validate_model_has_attribute(ConcreteOptionModel, "selection_model")

                    validate_model_relationship(
                        ConcreteOptionModel, "selection_model", str
                    )

                    validate_model_is_concrete(ConcreteOptionModel)

                    # Check if 'associated_tenants' field already exists to prevent duplicate field creation
                    # Critical for PostgreSQL tests where metaclasses can run multiple times
                    if not hasattr(
                        ConcreteOptionModel, "associated_tenants"
                    ) or "associated_tenants" not in [
                        f.name for f in ConcreteOptionModel._meta.get_fields()
                    ]:
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

                        logger.debug(
                            "Validating associated_tenants field after adding it to %s",
                            name,
                        )
                        validate_model_relationship(
                            ConcreteOptionModel,
                            "associated_tenants",
                            models.ManyToManyField,
                        )
                    else:
                        logger.debug(
                            "Field 'associated_tenants' already exists on %s, skipping add_to_class",
                            name,
                        )

        except Exception as e:
            logger.exception("Error creating model %s in OptionModelBase: %s", name, e)
            raise
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
        model = None

        try:
            model = super().__new__(cls, name, bases, attrs, **kwargs)
            for base in bases:
                if base.__name__ == "AbstractSelection":
                    ConcreteSelectionModel = model  # pylint: disable=C0103

                    validate_model_has_attribute(ConcreteSelectionModel, "option_model")
                    validate_model_has_attribute(
                        ConcreteSelectionModel, "option_on_delete"
                    )

                    validate_model_relationship(
                        ConcreteSelectionModel, "option_model", str
                    )
                    validate_model_relationship(
                        ConcreteSelectionModel, "option_on_delete", models.Field
                    )

                    validate_model_is_concrete(ConcreteSelectionModel)

                    # Check if 'option' field already exists to prevent duplicate field creation
                    # Critical for PostgreSQL tests where metaclasses can run multiple times
                    if not hasattr(
                        ConcreteSelectionModel, "option"
                    ) or "option" not in [
                        f.name for f in ConcreteSelectionModel._meta.get_fields()
                    ]:
                        # Allow field to be required (remove blank=True, null=True)
                        ConcreteSelectionModel.add_to_class(
                            "option",
                            model_config.foreignkey_class(
                                ConcreteSelectionModel.option_model,
                                on_delete=ConcreteSelectionModel.option_on_delete,
                                related_name=ConcreteSelectionModel.option_model_related_name,
                                related_query_name=ConcreteSelectionModel.option_model_related_query_name,
                            ),
                        )

                        logger.debug(
                            "Validating option field after adding it to %s", name
                        )
                        validate_model_relationship(
                            ConcreteSelectionModel,
                            "option",
                            model_config.foreignkey_class,
                        )
                    else:
                        logger.debug(
                            "Field 'option' already exists on %s, skipping add_to_class",
                            name,
                        )

        except Exception as e:
            logger.exception(
                "Error creating model %s in SelectionModelBase: %s", name, e
            )
            raise
        return model


class OptionQuerySet(model_config.queryset_class):
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

    def selected_options_for_tenant(
        self, tenant, include_deleted=False
    ) -> models.QuerySet:
        """Returns a QuerySet of the AbstractOption subclassed model.

        Includes all *selected* options for a given tenant, including:

        - all mandatory default options
        - all selected optional default options for this tenant
        - all selected custom options for this tenant

        Set `include_deleted=True` to include deleted options.
        """
        logger.debug(
            "Called selected_options_for_tenant in OptionQuerySet with %s, %s",
            tenant,
            include_deleted,
        )

        try:
            SelectionModel = self.model.associated_tenants.through  # pylint: disable=C0103
            selections = (
                SelectionModel.objects.active()
                .filter(tenant=tenant)
                .values_list("option", flat=True)
            )

            base_query = Q(option_type=OptionType.MANDATORY) | (
                Q(id__in=selections)
                & (
                    Q(option_type=OptionType.OPTIONAL)
                    | Q(option_type=OptionType.CUSTOM, tenant=tenant)
                )
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


class OptionManager(model_config.manager_class):
    """Manager for Option models.

    Provides methods for creating default options and filtering out deleted options.

    Subclass this manager to provide additional functionality for your concrete Option model.
    """

    def create_for_tenant(self, tenant, name: str):
        """Provided a tenant and a option name, creates the new option for that tenant."""
        try:
            logger.debug(
                "Creating custom option for tenant: %s",
                {"tenant_id": getattr(tenant, "id", None), "name": name},
            )

            # Validate tenant exists
            if not tenant:
                raise ValueError(
                    "Tenant must be provided when creating a custom option"
                )

            # Check for name conflicts
            if self.filter(
                name=name, option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL]
            ).exists():
                raise ValidationError(
                    f'Cannot create custom option with name "{name}" as it conflicts with an existing default option'
                )

            option = self.create(
                tenant=tenant, name=name, option_type=OptionType.CUSTOM
            )

            logger.info(
                "Successfully created custom option: %s",
                {
                    "id": option.id,
                    "name": name,
                    "tenant_id": getattr(tenant, "id", None),
                },
            )

            return option

        except Exception as e:
            logger.error(
                "Error creating custom option: %s",
                {
                    "tenant_id": getattr(tenant, "id", None),
                    "name": name,
                    "error": str(e),
                },
            )
            raise

    def create_mandatory(self, name: str):
        """Provided an option name, creates the new option (mandatorily selected for all tenants)."""
        return self.create(name=name, option_type=OptionType.MANDATORY)

    def create_optional(self, name: str):
        """Provided an option name, creates the new optional option (selectable by all tenants)."""
        return self.create(name=name, option_type=OptionType.OPTIONAL)

    def _update_or_create_default_option(
        self, item_name: str, options_dict: dict = dict
    ):
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
                option_type = (
                    value  # Set the option_type variable to the value provided
                )
                if option_type not in [OptionType.MANDATORY, OptionType.OPTIONAL]:
                    raise InvalidDefaultOptionError(
                        f"Option defaults must be of type `OptionType.MANDATORY` or `OptionType.OPTIONAL`. "
                        f"You specified {key} = {value} for {item_name=}."
                    )

        self.model.objects.update_or_create(
            name=item_name,
            option_type=option_type,
            defaults={
                "deleted": None
            },  # Undelete the option if it was previously deleted
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
            except Exception as e:  # pylint: disable=W0718
                logger.error("Error updating option %s: %s", name, e)

        # Soft delete options no longer in defaults
        existing_options = self.model.objects.filter(
            option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL],
            deleted__isnull=True,
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

    # Allow both required and optional tenant relationships based on option type
    condition = Q(option_type=OptionType.CUSTOM, tenant__isnull=False) | Q(
        option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL], tenant__isnull=True
    )

    return {
        get_condition_argument_name(): condition,
        "name": "%(app_label)s_%(class)s_tenant_check",
    }


class AbstractOption(model_config.model_class, metaclass=OptionModelBase):
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
    unscoped = model_config.manager_class()

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
        default_related_name = "%(app_label)s_%(class)s_option"

    def delete(self, using=None, keep_parents=False, override=False):
        """Delete the option, with option for hard delete.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent models
            override: If True, perform a hard delete. Otherwise, perform a soft delete.
        """
        try:
            logger.debug(
                "Attempting to delete option: %s",
                {"id": self.id, "name": self.name, "override": override},
            )

            if override:
                # Update related selections
                selection_model_class = apps.get_model(self.selection_model)
                selections_count = selection_model_class.objects.filter(
                    option=self
                ).count()
                logger.info(
                    "Updating related selections before hard delete: %s",
                    {"option_id": self.id, "selections_count": selections_count},
                )

                selection_model_class.objects.filter(option=self).update(
                    deleted=timezone.now()
                )
                result = super().delete(using=using, keep_parents=keep_parents)
                logger.info(
                    "Hard deleted option and updated selections: %s",
                    {"option_id": self.id, "deleted_count": result[0] if result else 0},
                )
                return result

            # Soft delete
            self.deleted = timezone.now()
            self.save()
            logger.info("Soft deleted option: %s", {"id": self.id, "name": self.name})

        except Exception as e:
            logger.error(
                "Error deleting option: %s",
                {"id": self.id, "name": self.name, "error": str(e)},
            )
            raise

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

    @classmethod
    def check(cls, **kwargs):
        """Check that the model has at least one manager that inherits from OptionManager and uses OptionQuerySet."""
        errors = super().check(**kwargs)

        if cls._meta.abstract:
            return errors

        managers = get_all_managers(cls)
        has_valid_manager = False

        for manager in managers:
            results = check_manager_compliance(
                cls, manager, OptionManager, OptionQuerySet, ("001", "002")
            )
            errors.extend(results)

            # Check if this manager is fully compliant
            if not any(isinstance(r, Error) for r in results):
                has_valid_manager = True

        if not has_valid_manager:
            errors.append(
                Error(
                    f"Model {cls.__name__} must have at least one manager that inherits from OptionManager "
                    "and uses OptionQuerySet",
                    obj=cls,
                    id="django_tenant_options.E003",
                )
            )

        # Check for Meta inheritance - validate expected constraints are present
        constraint_names = [
            c.name % {"app_label": cls._meta.app_label, "class": cls._meta.model_name}
            for c in cls._meta.constraints
        ]

        # Expected constraints from AbstractOption.Meta
        expected_unique_constraint = (
            f"{cls._meta.app_label}_{cls._meta.model_name}_unique_name"
        )
        expected_check_constraint = (
            f"{cls._meta.app_label}_{cls._meta.model_name}_tenant_check"
        )

        if expected_unique_constraint not in constraint_names:
            errors.append(
                Warning(
                    f"Model {cls.__name__} may be missing the unique name constraint. "
                    f"Ensure the Meta class inherits from AbstractOption.Meta to preserve database constraints. "
                    f"Example: class Meta(AbstractOption.Meta): ...",
                    obj=cls,
                    id="django_tenant_options.W007",
                )
            )

        if expected_check_constraint not in constraint_names:
            errors.append(
                Warning(
                    f"Model {cls.__name__} may be missing the tenant check constraint. "
                    f"Ensure the Meta class inherits from AbstractOption.Meta to preserve database constraints. "
                    f"Example: class Meta(AbstractOption.Meta): ...",
                    obj=cls,
                    id="django_tenant_options.W008",
                )
            )

        return errors

    def validate_option_tenant_relationship(self):
        """Validate option type and tenant relationship"""
        if self.option_type == OptionType.CUSTOM and not self.tenant_id:
            raise ValidationError("Custom options must have a tenant")
        elif (
            self.option_type in [OptionType.MANDATORY, OptionType.OPTIONAL]
            and self.tenant_id
        ):
            raise ValidationError("Default options cannot have a tenant")

    def clean(self):
        """Ensure no tenant can have the same name as a MANDATORY or OPTIONAL option."""
        try:
            # Validate option type and tenant relationship
            self.validate_option_tenant_relationship()

            # Check for name conflicts
            if self.option_type == OptionType.CUSTOM:
                conflicting = (
                    type(self)
                    .objects.filter(
                        name__iexact=self.name,
                        option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL],
                    )
                    .first()
                )
                if conflicting:
                    default_options = getattr(type(self), "default_options", {})
                    default_names = ", ".join(
                        f'"{name}"' for name in sorted(default_options.keys())
                    )

                    raise ValidationError(
                        f'Cannot create custom option "{self.name}" because it conflicts with an existing '
                        f"{conflicting.get_option_type_display()} option. "
                        f"Available default options: [{default_names}]. "
                        f'Suggestion: Choose a different name or select the existing "{conflicting.name}" option instead.'
                    )

            super().clean()

        except ValidationError as e:
            logger.error(
                "Option validation failed for %s: %s",
                self.__class__.__name__,
                str(e),
                extra={
                    "option_name": self.name,
                    "option_type": self.option_type,
                    "tenant_id": getattr(self.tenant, "id", None)
                    if self.tenant
                    else None,
                    "available_defaults": list(
                        getattr(type(self), "default_options", {}).keys()
                    ),
                },
            )
            raise

    def save(self, *args, **kwargs):
        """Ensure that the option is valid before saving."""
        try:
            logger.debug(
                "Validating option before save: %s",
                {
                    "name": self.name,
                    "option_type": self.option_type,
                    "tenant_id": getattr(self.tenant, "id", None),
                },
            )
            self.clean()
            super().save(*args, **kwargs)
            logger.info(
                "Successfully saved option: %s",
                {"id": self.id, "name": self.name, "option_type": self.option_type},
            )
        except ValidationError as e:
            logger.error(
                "Validation error saving option: %s",
                {"name": self.name, "option_type": self.option_type, "error": str(e)},
            )
            raise


class SelectionQuerySet(model_config.queryset_class):
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


class SelectionManager(model_config.manager_class):
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
            return OptionsModel.objects.options_for_tenant(
                tenant=tenant, include_deleted=include_deleted
            )
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
        logger.debug(
            "Called selected_options_for_tenant in SelectionManager with %s, %s",
            tenant,
            include_deleted,
        )
        try:
            OptionsModel = apps.get_model(self.model.option_model)  # pylint: disable=C0103
            return OptionsModel.objects.selected_options_for_tenant(
                tenant=tenant, include_deleted=include_deleted
            )
        except LookupError as e:
            # no such model in this application
            logger.warning(e)
            return None


class AbstractSelection(model_config.model_class, metaclass=SelectionModelBase):
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
    unscoped = model_config.manager_class()

    class Meta:  # pylint: disable=R0903
        """Meta options for AbstractSelection.

        Subclass this in your concrete model's Meta class to enforce constraints on the model.
        """

        verbose_name = _("Selection")
        verbose_name_plural = _("Selections")
        constraints = [
            # Prevent selections with invalid option references
            models.CheckConstraint(
                check=~Q(option_id__isnull=True),
                name="%(app_label)s_%(class)s_option_not_null",
            ),
            # Prevent selections with invalid tenant references
            models.CheckConstraint(
                check=~Q(tenant_id__isnull=True),
                name="%(app_label)s_%(class)s_tenant_not_null",
            ),
            # Prevent duplicate selections
            models.UniqueConstraint(
                fields=["tenant", "option"],
                condition=Q(deleted__isnull=True),
                name="%(app_label)s_%(class)s_unique_active_selection",
            ),
        ]
        abstract = True

    def clean(self):
        """Ensure that the selected option is available to the tenant."""
        try:
            logger.debug(
                "Validating selection: %s",
                {
                    "tenant_id": getattr(self.tenant, "id", None),
                    "option_id": getattr(self.option, "id", None),
                },
            )

            # Validate option exists
            if not self.option_id:
                raise ValidationError(
                    "Option must be specified. Please select an option from the available choices."
                )

            # Validate tenant exists
            if not self.tenant_id:
                raise ValidationError(
                    "Tenant must be specified. This selection cannot be created without a tenant."
                )

            # Validate option is active
            if getattr(self.option, "deleted", None):
                # Get active options for helpful error message
                try:
                    from django.apps import apps

                    OptionModel = apps.get_model(self.option_model)  # pylint: disable=C0103
                    active_count = OptionModel.objects.selected_options_for_tenant(
                        self.tenant
                    ).count()
                    raise ValidationError(
                        f'Cannot select deleted option "{self.option.name}". '
                        f"This option was deleted on {self.option.deleted.strftime('%Y-%m-%d')}. "
                        f"Suggestion: Choose from the {active_count} active options available to this tenant."
                    )
                except Exception:  # pylint: disable=W0718
                    raise ValidationError(
                        f'Cannot select deleted option "{self.option.name}". '
                        "Suggestion: Choose an active option instead."
                    )

            # Check tenant ownership
            if self.option.tenant and self.option.tenant != self.tenant:
                raise ValidationError(
                    f'The custom option "{self.option.name}" belongs to "{self.option.tenant}" '
                    f'and cannot be selected by "{self.tenant}". '
                    f"Suggestion: Create a custom option with this name for your tenant, "
                    f"or select from the available default options."
                )

            # Additional FK validation logic
            try:
                # Force DB hit to validate FKs exist
                self.tenant.refresh_from_db()
                self.option.refresh_from_db()
            except (AttributeError, ObjectDoesNotExist) as e:
                raise ValidationError(
                    f"Invalid relationship: {str(e)}. "
                    "The option or tenant may have been deleted. Please refresh and try again."
                ) from e

            super().clean()

            logger.debug(
                "Selection validation passed: %s",
                {"tenant_id": self.tenant_id, "option_id": self.option_id},
            )

        except ValidationError as e:
            logger.error(
                "Selection validation failed for %s: %s",
                self.__class__.__name__,
                str(e),
                extra={
                    "tenant_id": getattr(self.tenant, "id", None),
                    "tenant_name": str(self.tenant) if self.tenant else None,
                    "option_id": getattr(self.option, "id", None),
                    "option_name": getattr(self.option, "name", None),
                    "option_type": getattr(self.option, "option_type", None),
                    "option_deleted": getattr(self.option, "deleted", None) is not None,
                },
            )
            raise

    def save(self, *args, **kwargs):
        """Ensure that the selection is valid before saving."""
        try:
            self.clean()
            super().save(*args, **kwargs)
            logger.info(
                "Successfully saved selection: tenant=%s, option=%s",
                getattr(self.tenant, "id", None),
                getattr(self.option, "id", None),
            )
        except Exception as e:
            logger.error(
                "Failed to save selection: %s\n%s", str(e), traceback.format_exc()
            )
            raise

    def delete(self, using=None, keep_parents=False, override=False):
        """Delete the selection, with option for hard delete.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent models
            override: If True, perform a hard delete. Otherwise, perform a soft delete
        """
        if override:
            return super().delete(using=using, keep_parents=keep_parents)
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

    @classmethod
    def check(cls, **kwargs):
        """Check that model has at least one manager that inherits from SelectionManager and uses SelectionQuerySet."""
        errors = super().check(**kwargs)

        if cls._meta.abstract:
            return errors

        managers = get_all_managers(cls)
        has_valid_manager = False

        for manager in managers:
            results = check_manager_compliance(
                cls, manager, SelectionManager, SelectionQuerySet, ("004", "005")
            )
            errors.extend(results)

            # Check if this manager is fully compliant
            if not any(isinstance(r, Error) for r in results):
                has_valid_manager = True

        if not has_valid_manager:
            errors.append(
                Error(
                    f"Model {cls.__name__} must have at least one manager that inherits from SelectionManager "
                    "and uses SelectionQuerySet",
                    obj=cls,
                    id="django_tenant_options.E006",
                )
            )

        # Check for Meta inheritance - validate expected constraints are present
        constraint_names = [
            c.name % {"app_label": cls._meta.app_label, "class": cls._meta.model_name}
            for c in cls._meta.constraints
        ]

        # Expected constraints from AbstractSelection.Meta
        expected_option_check = (
            f"{cls._meta.app_label}_{cls._meta.model_name}_option_not_null"
        )
        expected_tenant_check = (
            f"{cls._meta.app_label}_{cls._meta.model_name}_tenant_not_null"
        )
        expected_unique_constraint = (
            f"{cls._meta.app_label}_{cls._meta.model_name}_unique_active_selection"
        )

        if expected_option_check not in constraint_names:
            errors.append(
                Warning(
                    f"Model {cls.__name__} may be missing the option_not_null check constraint. "
                    f"Ensure the Meta class inherits from AbstractSelection.Meta to preserve database constraints. "
                    f"Example: class Meta(AbstractSelection.Meta): ...",
                    obj=cls,
                    id="django_tenant_options.W009",
                )
            )

        if expected_tenant_check not in constraint_names:
            errors.append(
                Warning(
                    f"Model {cls.__name__} may be missing the tenant_not_null check constraint. "
                    f"Ensure the Meta class inherits from AbstractSelection.Meta to preserve database constraints. "
                    f"Example: class Meta(AbstractSelection.Meta): ...",
                    obj=cls,
                    id="django_tenant_options.W010",
                )
            )

        if expected_unique_constraint not in constraint_names:
            errors.append(
                Warning(
                    f"Model {cls.__name__} may be missing the unique active selection constraint. "
                    f"Ensure the Meta class inherits from AbstractSelection.Meta to preserve database constraints. "
                    f"Example: class Meta(AbstractSelection.Meta): ...",
                    obj=cls,
                    id="django_tenant_options.W011",
                )
            )

        return errors
