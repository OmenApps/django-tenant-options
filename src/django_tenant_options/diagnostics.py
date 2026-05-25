"""Pure, importable diagnostics for django-tenant-options configuration.

This module performs all of the configuration checks used by the
``validateoptions`` management command. Keeping the logic here, separate from
the command's stdout rendering, lets tests assert on a structured result
instead of parsing console output.
"""

import logging
from dataclasses import dataclass
from dataclasses import field

from django.db.models import Count

from django_tenant_options.choices import OptionType
from django_tenant_options.helpers import all_option_subclasses
from django_tenant_options.helpers import all_selection_subclasses
from django_tenant_options.models import OptionManager
from django_tenant_options.models import SelectionManager


logger = logging.getLogger("django_tenant_options")


@dataclass
class DiagnosticsResult:
    """Structured result of a diagnostics run.

    Attributes:
        errors: Blocking problems. The command exits non-zero when any exist.
        warnings: Non-blocking advisories. Promoted to errors under ``--strict``.
        infos: Per-model "OK" checklist lines (e.g. "manager configured").
    """

    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    infos: list = field(default_factory=list)

    @property
    def has_errors(self):
        """Return True when at least one error was recorded."""
        return bool(self.errors)

    @property
    def has_warnings(self):
        """Return True when at least one warning was recorded."""
        return bool(self.warnings)

    @property
    def passed_count(self):
        """Return the number of passed-check (info) lines."""
        return len(self.infos)


def check_option_model(model, result):
    """Run all configuration checks for a single Option model.

    Appends error/warning/info strings to the given DiagnosticsResult.
    """
    name = model.__name__

    # Check manager setup
    if not hasattr(model, "objects"):
        result.errors.append(f"{name}: Missing 'objects' manager")
    else:
        if not isinstance(model.objects, OptionManager):
            result.warnings.append(
                f"{name}: Manager 'objects' doesn't inherit from OptionManager. Filtering may not work as expected."
            )
        result.infos.append(f"{name}: manager configured")

    # Validate selection_model is set
    if not getattr(model, "selection_model", None):
        result.errors.append(f"{name}: selection_model attribute not set")
    else:
        result.infos.append(f"{name}: selection_model = {model.selection_model}")

    # Validate tenant_model is set
    if not getattr(model, "tenant_model", None):
        result.errors.append(f"{name}: tenant_model attribute not set")
    else:
        result.infos.append(f"{name}: tenant_model = {model.tenant_model}")

    # Validate default_options format
    default_options = getattr(model, "default_options", {})
    if default_options:
        result.infos.append(f"{name}: {len(default_options)} default options defined")
        for option_name, config in default_options.items():
            if "option_type" in config and config["option_type"] not in [
                OptionType.MANDATORY,
                OptionType.OPTIONAL,
            ]:
                result.errors.append(
                    f"{name}: Invalid option_type for default option '{option_name}'. "
                    f"Must be OptionType.MANDATORY or OptionType.OPTIONAL, got {config['option_type']}"
                )
    elif getattr(model, "default_options_allow_empty", False):
        result.infos.append(f"{name}: no default_options (intentionally empty)")
    else:
        result.warnings.append(
            f"{name}: No default_options defined. Consider defining mandatory or optional defaults for consistency."
        )

    # Check for naming conflicts in database
    try:
        duplicates = (
            model.objects.filter(
                option_type__in=[OptionType.MANDATORY, OptionType.OPTIONAL],
                deleted__isnull=True,
            )
            .values("name")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )
        if duplicates.exists():
            dup_names = [d["name"] for d in duplicates]
            result.warnings.append(
                f"{name}: Duplicate default option names found in database: {dup_names}. "
                "This may cause unexpected behavior."
            )
    except Exception as e:  # pylint: disable=W0718
        logger.debug("%s: duplicate-name check failed: %s", name, e, exc_info=True)
        result.warnings.append(f"{name}: Could not check for duplicates in database: {e}")

    # Validate Meta inheritance by checking for expected constraints
    constraint_names = [
        c.name % {"app_label": model._meta.app_label, "class": model._meta.model_name} for c in model._meta.constraints
    ]
    expected_unique = f"{model._meta.app_label}_{model._meta.model_name}_unique_name"
    expected_check = f"{model._meta.app_label}_{model._meta.model_name}_tenant_check"

    if expected_unique not in constraint_names:
        result.warnings.append(
            f"{name}: Missing unique name constraint. Ensure Meta class inherits from AbstractOption.Meta"
        )
    if expected_check not in constraint_names:
        result.warnings.append(
            f"{name}: Missing tenant check constraint. Ensure Meta class inherits from AbstractOption.Meta"
        )
    if expected_unique in constraint_names and expected_check in constraint_names:
        result.infos.append(f"{name}: database constraints properly configured")


def check_selection_model(model, result):
    """Run all configuration checks for a single Selection model.

    Appends error/warning/info strings to the given DiagnosticsResult.
    """
    name = model.__name__

    # Check manager setup
    if not hasattr(model, "objects"):
        result.errors.append(f"{name}: Missing 'objects' manager")
    else:
        if not isinstance(model.objects, SelectionManager):
            result.warnings.append(
                f"{name}: Manager 'objects' doesn't inherit from SelectionManager. Filtering may not work as expected."
            )
        result.infos.append(f"{name}: manager configured")

    # Validate option_model is set
    if not getattr(model, "option_model", None):
        result.errors.append(f"{name}: option_model attribute not set")
    else:
        result.infos.append(f"{name}: option_model = {model.option_model}")

    # Validate tenant_model is set
    if not getattr(model, "tenant_model", None):
        result.errors.append(f"{name}: tenant_model attribute not set")
    else:
        result.infos.append(f"{name}: tenant_model = {model.tenant_model}")

    # Check for orphaned selections (active selections pointing to deleted options)
    try:
        if hasattr(model, "objects") and getattr(model, "option_model", None):
            orphaned = model.objects.filter(option__deleted__isnull=False, deleted__isnull=True).count()
            if orphaned > 0:
                result.warnings.append(
                    f"{name}: Found {orphaned} active selection(s) pointing to deleted options. "
                    "Consider running data cleanup."
                )
            else:
                result.infos.append(f"{name}: no orphaned selections found")
    except Exception as e:  # pylint: disable=W0718
        logger.debug("%s: orphaned-selection check failed: %s", name, e, exc_info=True)
        result.warnings.append(f"{name}: Could not check for orphaned selections: {e}")

    # Validate Meta inheritance by checking for expected constraints
    constraint_names = [
        c.name % {"app_label": model._meta.app_label, "class": model._meta.model_name} for c in model._meta.constraints
    ]
    expected_option_check = f"{model._meta.app_label}_{model._meta.model_name}_option_not_null"
    expected_tenant_check = f"{model._meta.app_label}_{model._meta.model_name}_tenant_not_null"
    expected_unique = f"{model._meta.app_label}_{model._meta.model_name}_unique_active_selection"

    missing_constraints = []
    if expected_option_check not in constraint_names:
        missing_constraints.append("option_not_null")
    if expected_tenant_check not in constraint_names:
        missing_constraints.append("tenant_not_null")
    if expected_unique not in constraint_names:
        missing_constraints.append("unique_active_selection")

    if missing_constraints:
        result.warnings.append(
            f"{name}: Missing constraints: {', '.join(missing_constraints)}. "
            "Ensure Meta class inherits from AbstractSelection.Meta"
        )
    else:
        result.infos.append(f"{name}: database constraints properly configured")


def run_diagnostics(option_resolver=None, selection_resolver=None):
    """Run all django-tenant-options configuration checks and return a DiagnosticsResult.

    This is a pure function: it performs no console output and raises no SystemExit.
    Callers (e.g. the validateoptions command) decide how to render and how to exit.

    Scope: this runs package-wide across every concrete Option and Selection model
    and is NOT scoped to any tenant. It is intended as an administrator / CI
    configuration check, not a per-tenant or end-user facing operation.

    The resolver arguments default to the module-level helper functions. They exist
    so callers can inject alternative model lists (used by the command to forward
    test-time monkeypatched resolvers).
    """
    if option_resolver is None:
        option_resolver = all_option_subclasses
    if selection_resolver is None:
        selection_resolver = all_selection_subclasses

    result = DiagnosticsResult()

    option_models = option_resolver()
    if not option_models:
        result.warnings.append("No Option models found. Have you created any concrete Option subclasses?")
    for model in option_models:
        check_option_model(model, result)

    selection_models = selection_resolver()
    if not selection_models:
        result.warnings.append("No Selection models found. Have you created any concrete Selection subclasses?")
    for model in selection_models:
        check_selection_model(model, result)

    return result
