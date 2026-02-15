"""Command to validate django-tenant-options configuration."""

import logging
import sys

from django.core.management.base import BaseCommand
from django.db.models import Count

from django_tenant_options.choices import OptionType
from django_tenant_options.helpers import all_option_subclasses
from django_tenant_options.helpers import all_selection_subclasses
from django_tenant_options.models import OptionManager
from django_tenant_options.models import SelectionManager


logger = logging.getLogger("django_tenant_options")


class Command(BaseCommand):
    """Validate django-tenant-options configuration."""

    help = "Validates all Option and Selection models are properly configured"

    def handle(self, *args, **options):
        """Run validation checks."""
        errors = []
        warnings = []

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.MIGRATE_HEADING("  Django Tenant Options Configuration Validation"))
        self.stdout.write("=" * 70 + "\n")

        # Check all Option subclasses
        self.stdout.write(self.style.MIGRATE_LABEL("\nValidating Option Models..."))
        option_models = all_option_subclasses()

        if not option_models:
            warnings.append("No Option models found. Have you created any concrete Option subclasses?")
        else:
            self.stdout.write(f"Found {len(option_models)} Option model(s)\n")

        for model in option_models:
            self._validate_option_model(model, errors, warnings)

        # Check all Selection subclasses
        self.stdout.write(self.style.MIGRATE_LABEL("\nValidating Selection Models..."))
        selection_models = all_selection_subclasses()

        if not selection_models:
            warnings.append("No Selection models found. Have you created any concrete Selection subclasses?")
        else:
            self.stdout.write(f"Found {len(selection_models)} Selection model(s)\n")

        for model in selection_models:
            self._validate_selection_model(model, errors, warnings)

        # Output results
        self.stdout.write("\n" + "=" * 70)
        if errors:
            self.stdout.write(self.style.ERROR("\nERRORS FOUND:"))
            self.stdout.write(self.style.ERROR("=" * 70))
            for i, error in enumerate(errors, 1):
                self.stdout.write(self.style.ERROR(f"\n{i}. {error}"))

        if warnings:
            self.stdout.write(self.style.WARNING("\n\nWARNINGS:"))
            self.stdout.write(self.style.WARNING("=" * 70))
            for i, warning in enumerate(warnings, 1):
                self.stdout.write(self.style.WARNING(f"\n{i}. {warning}"))

        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS("\nAll validations passed!"))
            self.stdout.write(self.style.SUCCESS("\nYour django-tenant-options configuration is properly set up."))

        self.stdout.write("\n" + "=" * 70 + "\n")

        # Exit with error code if errors found (useful for CI/CD)
        if errors:
            sys.exit(1)

    def _validate_option_model(self, model, errors, warnings):
        """Validate a single Option model."""
        self.stdout.write(f"\n  Checking {model.__name__}...")

        # Check manager setup
        if not hasattr(model, "objects"):
            errors.append(f"{model.__name__}: Missing 'objects' manager")
        else:
            # Check manager inheritance
            if not isinstance(model.objects, OptionManager):
                warnings.append(
                    f"{model.__name__}: Manager 'objects' doesn't inherit from OptionManager. "
                    f"Filtering may not work as expected."
                )
            self.stdout.write("    Manager configured")

        # Validate selection_model is set
        if not hasattr(model, "selection_model") or not model.selection_model:
            errors.append(f"{model.__name__}: selection_model attribute not set")
        else:
            self.stdout.write(f"    selection_model = {model.selection_model}")

        # Validate tenant_model is set
        if not hasattr(model, "tenant_model") or not model.tenant_model:
            errors.append(f"{model.__name__}: tenant_model attribute not set")
        else:
            self.stdout.write(f"    tenant_model = {model.tenant_model}")

        # Validate default_options format
        default_options = getattr(model, "default_options", {})
        if default_options:
            self.stdout.write(f"    {len(default_options)} default options defined")

            for name, config in default_options.items():
                if "option_type" in config:
                    if config["option_type"] not in [
                        OptionType.MANDATORY,
                        OptionType.OPTIONAL,
                    ]:
                        errors.append(
                            f"{model.__name__}: Invalid option_type for default option '{name}'. "
                            f"Must be OptionType.MANDATORY or OptionType.OPTIONAL, got {config['option_type']}"
                        )
        else:
            warnings.append(
                f"{model.__name__}: No default_options defined. "
                "Consider defining mandatory or optional defaults for consistency."
            )

        # Check for naming conflicts in database
        try:
            # Check for duplicate default option names
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
                warnings.append(
                    f"{model.__name__}: Duplicate default option names found in database: {dup_names}. "
                    "This may cause unexpected behavior."
                )
        except Exception as e:  # pylint: disable=W0718
            warnings.append(f"{model.__name__}: Could not check for duplicates in database: {str(e)}")

        # Validate Meta inheritance by checking for expected constraints
        constraint_names = [
            c.name % {"app_label": model._meta.app_label, "class": model._meta.model_name}
            for c in model._meta.constraints
        ]

        expected_unique = f"{model._meta.app_label}_{model._meta.model_name}_unique_name"
        expected_check = f"{model._meta.app_label}_{model._meta.model_name}_tenant_check"

        if expected_unique not in constraint_names:
            warnings.append(
                f"{model.__name__}: Missing unique name constraint. Ensure Meta class inherits from AbstractOption.Meta"
            )

        if expected_check not in constraint_names:
            warnings.append(
                f"{model.__name__}: Missing tenant check constraint. "
                "Ensure Meta class inherits from AbstractOption.Meta"
            )

        if expected_unique in constraint_names and expected_check in constraint_names:
            self.stdout.write("    Database constraints properly configured")

    def _validate_selection_model(self, model, errors, warnings):
        """Validate a single Selection model."""
        self.stdout.write(f"\n  Checking {model.__name__}...")

        # Check manager setup
        if not hasattr(model, "objects"):
            errors.append(f"{model.__name__}: Missing 'objects' manager")
        else:
            # Check manager inheritance
            if not isinstance(model.objects, SelectionManager):
                warnings.append(
                    f"{model.__name__}: Manager 'objects' doesn't inherit from SelectionManager. "
                    f"Filtering may not work as expected."
                )
            self.stdout.write("    Manager configured")

        # Validate option_model is set
        if not hasattr(model, "option_model") or not model.option_model:
            errors.append(f"{model.__name__}: option_model attribute not set")
        else:
            self.stdout.write(f"    option_model = {model.option_model}")

        # Validate tenant_model is set
        if not hasattr(model, "tenant_model") or not model.tenant_model:
            errors.append(f"{model.__name__}: tenant_model attribute not set")
        else:
            self.stdout.write(f"    tenant_model = {model.tenant_model}")

        # Check for orphaned selections (active selections pointing to deleted options)
        try:
            if hasattr(model, "objects") and hasattr(model, "option_model"):
                from django.apps import apps

                _OptionModel = apps.get_model(model.option_model)  # noqa: F841
                orphaned = model.objects.filter(option__deleted__isnull=False, deleted__isnull=True).count()

                if orphaned > 0:
                    warnings.append(
                        f"{model.__name__}: Found {orphaned} active selection(s) pointing to deleted options. "
                        "Consider running data cleanup."
                    )
                else:
                    self.stdout.write("    No orphaned selections found")
        except Exception as e:  # pylint: disable=W0718
            warnings.append(f"{model.__name__}: Could not check for orphaned selections: {str(e)}")

        # Validate Meta inheritance by checking for expected constraints
        constraint_names = [
            c.name % {"app_label": model._meta.app_label, "class": model._meta.model_name}
            for c in model._meta.constraints
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
            warnings.append(
                f"{model.__name__}: Missing constraints: {', '.join(missing_constraints)}. "
                "Ensure Meta class inherits from AbstractSelection.Meta"
            )
        else:
            self.stdout.write("    Database constraints properly configured")
