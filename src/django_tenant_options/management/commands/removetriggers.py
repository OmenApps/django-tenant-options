"""Management command to generate migrations for removing triggers created by maketriggers command.

This module provides a Django management command that automatically generates database migrations
to remove triggers that were previously created for models inheriting from AbstractSelection.
"""

from __future__ import annotations

import re
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management.base import CommandParser
from django.db.migrations.recorder import MigrationRecorder

from django_tenant_options.models import AbstractSelection


@dataclass(frozen=True)  # Make the dataclass immutable which implements __hash__
class TriggerInfo:
    """Contains information about an identified trigger.

    This class is immutable and hashable, allowing it to be used in sets.
    Each instance is uniquely identified by the combination of
    trigger_name and migration_file.
    """

    trigger_name: str
    migration_file: Path
    model_name: str
    app_label: str

    def __eq__(self, other: object) -> bool:
        """Implement equality comparison.

        Args:
            other: Object to compare with

        Returns:
            True if objects are equal, False otherwise
        """
        if not isinstance(other, TriggerInfo):
            return NotImplemented
        return self.trigger_name == other.trigger_name and self.migration_file == other.migration_file

    def __hash__(self) -> int:
        """Implement hashing.

        Returns:
            Hash value for the object
        """
        return hash((self.trigger_name, str(self.migration_file)))


class Command(BaseCommand):
    """Management command to generate migrations that remove previously created triggers.

    This command scans existing migrations to identify triggers created by the maketriggers
    command and generates new migrations to remove them.
    """

    help = dedent(
        """\
        Generate migrations to remove triggers previously created by maketriggers command.

        This command will:
        1. Scan existing migrations to find triggers
        2. Create new migrations to drop the identified triggers
        3. Optionally verify trigger removal if --verify flag is used
        """
    )

    def __init__(self, *args, **kwargs):
        """Initialize command with default values for all configuration options."""
        super().__init__(*args, **kwargs)
        self.app_label: str | None = None
        self.model_name: str | None = None
        self.dry_run: bool = False
        self.migration_dir: str | None = None
        self.interactive: bool = False
        self.verbose: bool = False
        self.verify: bool = False
        self.last_generated_migration: str | None = None

    def create_parser(self, prog_name: str, subcommand: str, **kwargs) -> CommandParser:
        """Create a command parser that preserves newlines in help text.

        Args:
            prog_name: The name of the program
            subcommand: The name of the subcommand
            **kwargs: Additional parser arguments

        Returns:
            A CommandParser instance with RawTextHelpFormatter
        """
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command-line arguments to the parser.

        Args:
            parser: The argument parser to add arguments to
        """
        parser.add_argument(
            "--app",
            type=str,
            metavar="app_name",
            help="Specify the app to remove triggers from.",
        )
        parser.add_argument(
            "--model",
            type=str,
            metavar="app_name.ModelName",
            help="Specify the model to remove triggers for (format: app_label.ModelName).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Simulate the migration creation process without writing any files. "
                "Use with --verbose to see the migration file content that would be created."
            ),
        )
        parser.add_argument(
            "--migration-dir",
            type=str,
            metavar="directory",
            help="Specify a custom directory to save migration files.",
        )
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Prompt for confirmation before creating each migration.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Provide detailed output of the migration creation process.",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify that identified triggers exist in the database before removing.",
        )

    def handle(self, *args, **options) -> None:
        """Execute the command logic based on provided options.

        Args:
            *args: Positional arguments
            **options: Command options as key-value pairs
        """
        self._initialize_options(options)

        if self.model_name:
            app_label, model_name = self.model_name.split(".")
            self._handle_single_model(app_label, model_name)
        elif self.app_label:
            self._handle_app_models()
        else:
            self._handle_all_models()

    def _initialize_options(self, options: dict) -> None:
        """Initialize command options from parsed arguments.

        Args:
            options: Dictionary of command options
        """
        self.app_label = options.get("app")
        self.model_name = options.get("model")
        self.dry_run = options.get("dry_run", False)
        self.migration_dir = options.get("migration_dir")
        self.interactive = options.get("interactive", False)
        self.verbose = options.get("verbose", False)
        self.verify = options.get("verify", False)

    def _handle_single_model(self, app_label: str, model_name: str) -> None:
        """Process trigger removal for a single model.

        Args:
            app_label: Label of the Django app containing the model
            model_name: Name of the model class
        """
        model = apps.get_model(app_label, model_name)
        if not issubclass(model, AbstractSelection) or model == AbstractSelection:
            self.stdout.write(
                self.style.WARNING(f"Model {model_name} is not a subclass of AbstractSelection. Skipping...")
            )
            return

        triggers = self._find_triggers_for_model(app_label, model_name)
        self._process_triggers(triggers)

    def _handle_app_models(self) -> None:
        """Process trigger removal for all eligible models in the specified app."""
        app_config = apps.get_app_config(self.app_label)
        triggers = []

        for model in app_config.get_models():
            if issubclass(model, AbstractSelection) and model != AbstractSelection:
                triggers.extend(self._find_triggers_for_model(model._meta.app_label, model.__name__))

        self._process_triggers(triggers)

    def _handle_all_models(self) -> None:
        """Process trigger removal for all eligible models across all apps."""
        triggers = []

        for model in apps.get_models():
            if issubclass(model, AbstractSelection) and model != AbstractSelection:
                triggers.extend(self._find_triggers_for_model(model._meta.app_label, model.__name__))

        self._process_triggers(triggers)

    def _find_triggers_for_model(self, app_label: str, model_name: str) -> list[TriggerInfo]:
        """Find all triggers associated with a specific model.

        Args:
            app_label: Label of the Django app containing the model
            model_name: Name of the model class

        Returns:
            List of TriggerInfo objects for found triggers
        """
        triggers = []
        migrations_dir = self._get_migrations_dir(app_label)

        if not migrations_dir.exists():
            return triggers

        for migration_file in migrations_dir.glob("*.py"):
            content = migration_file.read_text()

            # Look for trigger names in the migration content
            trigger_pattern = re.compile(r"DROP TRIGGER IF EXISTS ([^;]+);")
            model_pattern = re.compile(rf"auto_trigger_{model_name.lower()}|trigger.*{model_name.lower()}")

            if model_pattern.search(migration_file.name):
                for match in trigger_pattern.finditer(content):
                    triggers.append(
                        TriggerInfo(
                            trigger_name=match.group(1),
                            migration_file=migration_file,
                            model_name=model_name,
                            app_label=app_label,
                        )
                    )

        return triggers

    def _process_triggers(self, triggers: list[TriggerInfo]) -> None:
        """Process the identified triggers and create removal migrations.

        Args:
            triggers: List of TriggerInfo objects to process
        """
        if not triggers:
            self.stdout.write(self.style.WARNING("No triggers found to remove."))
            return

        # Group triggers by app_label to create one migration per app
        triggers_by_app: dict[str, set[TriggerInfo]] = {}
        for trigger in triggers:
            triggers_by_app.setdefault(trigger.app_label, set()).add(trigger)

        for app_label, app_triggers in triggers_by_app.items():
            self._create_removal_migration(app_label, app_triggers)

    def _create_removal_migration(self, app_label: str, triggers: set[TriggerInfo]) -> None:
        """Create a migration to remove the specified triggers.

        Args:
            app_label: Label of the Django app
            triggers: Set of TriggerInfo objects for triggers to remove
        """
        migration_name = self._construct_migration_name(app_label)
        migration_path = self._get_migration_path(app_label, migration_name)

        if self.dry_run:
            self._handle_dry_run(migration_path, triggers)
            return

        if self.interactive and not self._confirm_creation(app_label, triggers):
            return

        migration_content = self._generate_migration_content(app_label, triggers)

        if not self.dry_run:
            migration_path.write_text(migration_content)
            self.stdout.write(self.style.SUCCESS(f"Created migration: {migration_path}"))

    def _construct_migration_name(self, app_label: str) -> str:
        """Construct a name for the new migration file.

        Args:
            app_label: Label of the Django app

        Returns:
            Constructed migration name
        """
        last_migration = MigrationRecorder.Migration.objects.filter(app=app_label).order_by("applied").last()

        if last_migration and (match := re.match(r"^(\d+)_", last_migration.name)):
            number = str(int(match.group(1)) + 1).zfill(4)
            return f"{number}_remove_triggers"

        return "remove_triggers"

    def _get_migration_path(self, app_label: str, migration_name: str) -> Path:
        """Get the full path for the new migration file.

        Args:
            app_label: Label of the Django app
            migration_name: Name of the migration file

        Returns:
            Path object for the migration file
        """
        migrations_dir = self._get_migrations_dir(app_label)
        migrations_dir.mkdir(exist_ok=True)
        return migrations_dir / f"{migration_name}.py"

    def _get_migrations_dir(self, app_label: str) -> Path:
        """Get the migrations directory for an app.

        Args:
            app_label: Label of the Django app

        Returns:
            Path object for the migrations directory
        """
        if self.migration_dir:
            return Path(self.migration_dir)
        return Path(apps.get_app_config(app_label).path) / "migrations"

    def _handle_dry_run(self, migration_path: Path, triggers: set[TriggerInfo]) -> None:
        """Handle dry run mode for migration creation.

        Args:
            migration_path: Path where the migration would be created
            triggers: Set of TriggerInfo objects for triggers to remove
        """
        self.stdout.write(self.style.SUCCESS(f"[DRY RUN] Would create migration: {migration_path}"))
        if self.verbose:
            self.stdout.write(f"[DRY RUN] Would remove triggers: {', '.join(t.trigger_name for t in triggers)}")

    def _confirm_creation(self, app_label: str, triggers: set[TriggerInfo]) -> bool:
        """Prompt for user confirmation in interactive mode.

        Args:
            app_label: Label of the Django app
            triggers: Set of TriggerInfo objects for triggers to remove

        Returns:
            Boolean indicating if the user confirmed
        """
        trigger_list = "\n  ".join(t.trigger_name for t in triggers)
        return (
            input(
                f"\nWill remove the following triggers from {app_label}:\n" f"  {trigger_list}\n" f"Proceed? (y/n): "
            ).lower()
            == "y"
        )

    def _generate_migration_content(self, app_label: str, triggers: set[TriggerInfo]) -> str:
        """Generate the content for the migration file.

        Args:
            app_label: Label of the Django app
            triggers: Set of TriggerInfo objects for triggers to remove

        Returns:
            String containing the migration file content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Get the last migration for dependencies
        last_migration = MigrationRecorder.Migration.objects.filter(app=app_label).order_by("applied").last()

        last_migration_name = last_migration.name if last_migration else None

        operations = []
        for trigger in triggers:
            operations.append(
                f"        migrations.RunSQL(\n"
                f"            sql='DROP TRIGGER IF EXISTS {trigger.trigger_name};',\n"
                f"            reverse_sql='',  # No reverse operation as this removes triggers\n"
                f"        ),"
            )

        return dedent(
            f"""\
        # Generated by django-tenant-options on {timestamp}

        from django.db import migrations


        class Migration(migrations.Migration):
            \"\"\"Removes triggers previously created by django-tenant-options.\"\"\"

            dependencies = [
                ('{app_label}', '{last_migration_name}'),
            ]

            operations = [
        {"".join(operations)}
            ]
        """
        )
