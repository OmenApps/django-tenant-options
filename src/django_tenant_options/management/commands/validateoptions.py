"""Command to validate django-tenant-options configuration (setup doctor)."""

import sys

from django.core.management.base import BaseCommand

from django_tenant_options.diagnostics import run_diagnostics
from django_tenant_options.helpers import all_option_subclasses
from django_tenant_options.helpers import all_selection_subclasses


class Command(BaseCommand):
    """Validate django-tenant-options configuration."""

    help = "Validates all Option and Selection models are properly configured"

    def add_arguments(self, parser):
        """Register optional flags."""
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress the per-model checklist; print only warnings, errors, and the summary.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat warnings as errors for the exit code (exit 1 if any warnings).",
        )

    def handle(self, *args, **options):
        """Run validation checks and render results."""
        quiet = options.get("quiet", False)
        strict = options.get("strict", False)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.MIGRATE_HEADING("  Django Tenant Options Configuration Validation"))
        self.stdout.write("=" * 70 + "\n")

        # Forward the (possibly monkeypatched) module-level resolvers so tests that
        # patch them on this command module continue to take effect.
        result = run_diagnostics(
            option_resolver=all_option_subclasses,
            selection_resolver=all_selection_subclasses,
        )

        if not quiet:
            self._render_checklist(result)

        self.stdout.write("\n" + "=" * 70)

        if result.errors:
            self.stdout.write(self.style.ERROR("\nERRORS FOUND:"))
            self.stdout.write(self.style.ERROR("=" * 70))
            for i, error in enumerate(result.errors, 1):
                self.stdout.write(self.style.ERROR(f"\n{i}. {error}"))

        if result.warnings:
            self.stdout.write(self.style.WARNING("\n\nWARNINGS:"))
            self.stdout.write(self.style.WARNING("=" * 70))
            for i, warning in enumerate(result.warnings, 1):
                self.stdout.write(self.style.WARNING(f"\n{i}. {warning}"))

        if not result.errors and not result.warnings:
            self.stdout.write(self.style.SUCCESS("\nAll validations passed!"))
            self.stdout.write(self.style.SUCCESS("\nYour django-tenant-options configuration is properly set up."))

        # Summary line (always printed, even with --quiet). A plaintext status word
        # is included so the outcome is unambiguous when color is stripped (CI logs,
        # piped output, color-blind terminals) - not conveyed by color alone.
        status = "FAILED" if result.errors else ("PASSED WITH WARNINGS" if result.warnings else "PASSED")
        summary = (
            f"{status} - Summary: {result.passed_count} checks passed, "
            f"{len(result.warnings)} warning(s), {len(result.errors)} error(s)"
        )
        if result.errors:
            self.stdout.write(self.style.ERROR(f"\n{summary}"))
        elif result.warnings:
            self.stdout.write(self.style.WARNING(f"\n{summary}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n{summary}"))

        self.stdout.write("\n" + "=" * 70 + "\n")

        # Exit with error code if errors found (useful for CI/CD).
        if result.errors:
            sys.exit(1)
        # Under --strict, warnings also fail the run.
        if strict and result.warnings:
            sys.exit(1)

    def _render_checklist(self, result):
        """Print the per-model info (passed-check) lines grouped by model name.

        Info lines are formatted as "<ModelName>: <detail>"; group by the model name
        prefix and print each detail with a check mark.
        """
        grouped = {}
        order = []
        for info in result.infos:
            model_name, _, detail = info.partition(": ")
            if model_name not in grouped:
                grouped[model_name] = []
                order.append(model_name)
            grouped[model_name].append(detail or info)

        for model_name in order:
            self.stdout.write(self.style.MIGRATE_LABEL(f"\n  {model_name}"))
            for detail in grouped[model_name]:
                self.stdout.write(f"    [x] {detail}")
