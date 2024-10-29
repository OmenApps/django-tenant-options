"""Management command to generate database trigger migrations for models subclassed from AbstractSelection.

This module provides a Django management command that automatically generates database migrations
containing triggers for models that inherit from AbstractSelection. These triggers ensure data
integrity by preventing mismatches between Tenants and their associated Options.
"""

from __future__ import annotations

import hashlib
import re
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Literal

from django.apps import AppConfig
from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management.base import CommandParser
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Model

from django_tenant_options.app_settings import DB_VENDOR_OVERRIDE
from django_tenant_options.models import AbstractSelection


# Type aliases for supported database vendors
DBVendor = Literal["sqlite", "postgresql", "mysql", "oracle"]


@dataclass
class MigrationContext:
    """Contains context information for migration generation."""

    app_label: str
    model_name: str
    db_table: str
    trigger_name: str
    migration_name: str | None = None


class Command(BaseCommand):
    """Management command to generate trigger migrations for AbstractSelection models.

    This command identifies models that inherit from AbstractSelection and generates
    appropriate database trigger migrations to ensure data integrity between
    Tenants and their associated Options.
    """

    help = dedent(
        """\
        Generate migrations with triggers for models subclassed from AbstractSelection.

        These triggers ensure there can never be mismatch between a Tenant and an associated Option.

        Note: This command always drops any existing trigger before creating a new one, so forcing the creation of
        migrations will not cause an OperationalError.
        """
    )

    def __init__(self, *args, **kwargs):
        """Initialize command with default values for all configuration options."""
        super().__init__(*args, **kwargs)
        self.context: MigrationContext | None = None
        self.force: bool = False
        self.dry_run: bool = False
        self.migration_dir: str | None = None
        self.interactive: bool = False
        self.verbose: bool = False
        self.last_generated_migration: str | None = None
        self.db_vendor: DBVendor = self._get_db_vendor()

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
            help="Specify the app to create migrations for.",
        )
        parser.add_argument(
            "--model",
            type=str,
            metavar="app_name.ModelName",
            help="Specify the model to create migrations for (format: app_label.ModelName).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation of migrations even if the trigger already exists.",
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
            "--db-vendor-override",
            type=str,
            metavar="vendor",
            choices=["sqlite", "postgresql", "mysql", "oracle"],
            default=DB_VENDOR_OVERRIDE,
            help=(
                "Override the database vendor to use for generating the trigger SQL. "
                "Available options: sqlite, postgresql, mysql, oracle."
            ),
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

    def handle(self, *args, **options) -> None:
        """Execute the command logic based on provided options.

        Args:
            *args: Positional arguments
            **options: Command options as key-value pairs
        """
        self._initialize_options(options)

        if options.get("model"):
            self._handle_single_model(options["model"])
        elif options.get("app"):
            self._handle_app_models(options["app"])
        else:
            self._handle_all_models()

    def _initialize_options(self, options: dict) -> None:
        """Initialize command options from parsed arguments.

        Args:
            options: Dictionary of command options
        """
        self.force = options.get("force", False)
        self.dry_run = options.get("dry_run", False)
        self.migration_dir = options.get("migration_dir")
        self.interactive = options.get("interactive", False)
        self.verbose = options.get("verbose", False)
        self.db_vendor = self._get_db_vendor(options.get("db_vendor_override"))

    def _get_db_vendor(self, override: str | None = None) -> DBVendor:
        """Determine the database vendor to use.

        Args:
            override: Optional vendor override value

        Returns:
            Database vendor identifier

        Raises:
            ValueError: If the determined vendor is not supported
        """
        vendor = override or DB_VENDOR_OVERRIDE or connection.vendor
        if vendor not in ("sqlite", "postgresql", "mysql", "oracle"):
            raise ValueError(f"Unsupported database backend: {vendor}")
        return vendor

    def _handle_single_model(self, model_path: str) -> None:
        """Process a single model specified by its path.

        Args:
            model_path: String in format "app_label.ModelName"
        """
        app_label, model_name = model_path.split(".")
        model = apps.get_model(app_label, model_name)
        self._process_model(model)

    def _handle_app_models(self, app_label: str) -> None:
        """Process all AbstractSelection models in the specified app.

        Args:
            app_label: Label of the Django app to process
        """
        app_config = apps.get_app_config(app_label)
        self._process_app_models(app_config)

    def _handle_all_models(self) -> None:
        """Process AbstractSelection models across all installed apps."""
        for model in apps.get_models():
            if self._should_process_model(model):
                self._process_model(model)

    def _process_app_models(self, app_config: AppConfig) -> None:
        """Process all eligible models in an app configuration.

        Args:
            app_config: Django app configuration object
        """
        for model in app_config.get_models():
            if self._should_process_model(model):
                self._process_model(model)

    @staticmethod
    def _should_process_model(model: type[Model]) -> bool:
        """Determine if a model should have triggers generated.

        Args:
            model: Django model class

        Returns:
            Boolean indicating if the model should be processed
        """
        return issubclass(model, AbstractSelection) and model != AbstractSelection

    def _process_model(self, model: type[Model]) -> None:
        """Process a single model for trigger migration generation.

        Args:
            model: Django model class to process
        """
        self.context = MigrationContext(
            app_label=model._meta.app_label,
            model_name=model.__name__.lower(),
            db_table=model._meta.db_table,
            trigger_name=self._construct_trigger_name(model._meta.db_table),
        )

        if self.verbose:
            self._log_model_processing()

        if not self.force and (migration_file := self._trigger_exists()):
            self._log_existing_trigger(migration_file)
            return

        self._create_migration()

    def _validate_identifier(self, identifier: str) -> bool:
        """Validate that an identifier contains only allowed characters.

        Args:
            identifier: The database identifier to validate

        Returns:
            bool: True if identifier is valid, False otherwise
        """
        # Only allow alphanumeric, underscore, and dot for schema qualified names
        return bool(re.match(r"^[a-zA-Z0-9_\.]+$", identifier))

    def _quote_identifier(self, identifier: str) -> str:
        """Properly quote a database identifier.

        Args:
            identifier: The database identifier to quote

        Returns:
            str: The properly quoted identifier

        Raises:
            ValueError: If identifier contains invalid characters
        """
        if not self._validate_identifier(identifier):
            raise ValueError(
                f"Invalid identifier {identifier}. Only alphanumeric characters, underscores, and dots are allowed."
            )

        # Handle schema qualified names
        parts = identifier.split(".")
        quoted_parts = [f'"{part}"' for part in parts]
        return ".".join(quoted_parts)

    def _construct_trigger_name(self, db_table: str) -> str:
        """Construct a valid trigger name for the given database table.

        Args:
            db_table: Name of the database table

        Returns:
            Constructed trigger name that is safe to use

        Raises:
            ValueError: If table name contains invalid characters
        """
        max_length = connection.ops.max_name_length() or 200

        # Remove quotes and schemas, replace dots with underscores
        cleaned_table = db_table.replace('"', "").replace(".", "_")

        if not self._validate_identifier(cleaned_table):
            raise ValueError(
                f"Invalid table name {db_table}. Only alphanumeric characters, underscores, and dots are allowed."
            )

        base_name = f"{cleaned_table}_tenant_check"
        name_hash = hashlib.sha1(base_name.encode(), usedforsecurity=False).hexdigest()[:10]

        # Ensure name starts with a letter
        if base_name[0] in ("_", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
            base_name = f"t{base_name[:-1]}"

        trigger_name = f"{base_name[:max_length - len(name_hash) - 1]}_{name_hash}"

        # Validate final trigger name
        if not self._validate_identifier(trigger_name):
            raise ValueError(f"Generated trigger name {trigger_name} contains invalid characters")

        return trigger_name

    def _create_migration(self) -> None:
        """Create a new migration file for the current model context."""
        if not self.context:
            raise RuntimeError("Migration context not initialized")

        last_migration = self._get_last_migration()
        self.context.migration_name = self._construct_migration_name(last_migration)
        self.last_generated_migration = self.context.migration_name
        migration_path = self._get_migration_path()

        if self.dry_run:
            self._handle_dry_run(migration_path)
        else:
            self._handle_migration_creation(migration_path, last_migration)

    def _get_last_migration(self) -> str | None:
        """Get the name of the last migration for the current app.

        Returns:
            Name of the last migration or None if no migrations exist
        """
        if self.last_generated_migration:
            return self.last_generated_migration

        last_migration = MigrationRecorder.Migration.objects.filter(app=self.context.app_label).last()

        return last_migration.name if last_migration else None

    def _construct_migration_name(self, last_migration: str | None) -> str:
        """Construct a name for the new migration file.

        Args:
            last_migration: Name of the last migration

        Returns:
            Constructed migration name
        """
        if last_migration and (match := re.match(r"^(\d+)_", last_migration)):
            number = str(int(match.group(1)) + 1).zfill(4)
            return f"{number}_auto_trigger_{self.context.model_name}"
        return f"auto_trigger_{self.context.model_name}"

    def _get_migration_path(self) -> Path:
        """Get the full path for the new migration file.

        Returns:
            Path object for the migration file
        """
        app_config = apps.get_app_config(self.context.app_label)
        base_dir = Path(self.migration_dir or app_config.path) / "migrations"
        base_dir.mkdir(exist_ok=True)
        return base_dir / f"{self.context.migration_name}.py"

    def _handle_dry_run(self, migration_path: Path) -> None:
        """Handle dry run mode for migration creation.

        Args:
            migration_path: Path where the migration would be created
        """
        self.stdout.write(self.style.SUCCESS(f"[DRY RUN] Migration would be created: {migration_path}"))
        if self.verbose:
            self.stdout.write(
                "[DRY RUN] Migration content:\n" f"{self._get_migration_content(self._get_last_migration())}"
            )

    def _handle_migration_creation(self, migration_path: Path, last_migration: str | None) -> None:
        """Handle actual migration file creation.

        Args:
            migration_path: Path where to create the migration
            last_migration: Name of the last migration
        """
        if self.interactive and not self._confirm_creation():
            self.stdout.write(self.style.WARNING(f"Migration creation for {self.context.model_name} skipped by user."))
            return

        self.stdout.write(self.style.WARNING(f"Creating migration for {self.context.model_name}..."))

        migration_path.write_text(self._get_migration_content(last_migration), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Migration created: {migration_path}"))

    def _confirm_creation(self) -> bool:
        """Prompt for user confirmation in interactive mode.

        Returns:
            Boolean indicating if the user confirmed
        """
        return input(f"Do you want to create a migration for {self.context.model_name}? (y/n): ").lower() == "y"

    def _get_migration_content(self, last_migration: str | None) -> str:
        """Generate the content for the migration file.

        Args:
            last_migration: Name of the last migration

        Returns:
            String containing the migration file content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        trigger_sql = self._get_trigger_sql()

        return dedent(
            f"""\
            # Generated by django-tenant-options on {timestamp}

            from django.db import migrations


            class Migration(migrations.Migration):
                \"\"\"Adds an auto-generated trigger for a django-tenant-options Selection model.\"\"\"

                dependencies = [
                    ('{self.context.app_label}', '{last_migration}'),
                ]

                operations = [
                    migrations.RunSQL(
                        sql=\"\"\"{trigger_sql}\"\"\",
                        reverse_sql=\"\"\"DROP TRIGGER IF EXISTS {self.context.trigger_name};\"\"\",
                    ),
                ]
            """
        )

    def _get_trigger_sql(self) -> str:
        """Generate the SQL for creating the database trigger.

        Returns:
            SQL string for creating the trigger

        Raises:
            ValueError: If the database vendor is not supported
        """
        if self.verbose:
            self._log_trigger_sql_generation()

        trigger_templates = {
            "sqlite": self._get_sqlite_trigger,
            "postgresql": self._get_postgresql_trigger,
            "mysql": self._get_mysql_trigger,
            "oracle": self._get_oracle_trigger,
        }

        return trigger_templates[self.db_vendor]()

    def _get_sqlite_trigger(self) -> str:
        """Generate SQLite-specific trigger SQL with proper quoting."""
        trigger_name = self._quote_identifier(self.context.trigger_name)
        table_name = self._quote_identifier(self.context.db_table)

        return f"""
            DROP TRIGGER IF EXISTS {trigger_name};
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT ON {table_name}
            FOR EACH ROW
            WHEN NEW.tenant_id != (SELECT tenant_id FROM {table_name} WHERE id = NEW.option_id)
            BEGIN
                SELECT RAISE(FAIL, 'Tenant mismatch between options and selections');
            END;
            """  # nosec

    def _get_postgresql_trigger(self) -> str:
        """Generate PostgreSQL-specific trigger SQL with proper quoting."""
        trigger_name = self._quote_identifier(self.context.trigger_name)
        table_name = self._quote_identifier(self.context.db_table)
        function_name = self._quote_identifier(f"{self.context.trigger_name}_func")

        return f"""
            CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.tenant_id != (SELECT tenant_id FROM {table_name} WHERE id = NEW.option_id) THEN
                    RAISE EXCEPTION 'Tenant mismatch between options and selections';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS {trigger_name} ON {table_name};
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION {function_name}();
            """  # nosec

    def _get_mysql_trigger(self) -> str:
        """Generate MySQL-specific trigger SQL with proper quoting."""
        trigger_name = self._quote_identifier(self.context.trigger_name)
        table_name = self._quote_identifier(self.context.db_table)

        return f"""
            DROP TRIGGER IF EXISTS {trigger_name};
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT ON {table_name}
            FOR EACH ROW
            BEGIN
                DECLARE option_tenant_id INT;
                SELECT tenant_id INTO option_tenant_id FROM {table_name} WHERE id = NEW.option_id;

                IF NEW.tenant_id != option_tenant_id THEN
                    SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Tenant mismatch between options and selections';
                END IF;
            END;
            """  # nosec

    def _get_oracle_trigger(self) -> str:
        """Generate Oracle-specific trigger SQL with proper quoting."""
        trigger_name = self._quote_identifier(self.context.trigger_name)
        table_name = self._quote_identifier(self.context.db_table)

        return f"""
            CREATE OR REPLACE TRIGGER {trigger_name}
            BEFORE INSERT ON {table_name}
            FOR EACH ROW
            DECLARE
                option_tenant_id NUMBER;
            BEGIN
                SELECT tenant_id INTO option_tenant_id FROM {table_name} WHERE id = :NEW.option_id;

                IF :NEW.tenant_id != option_tenant_id THEN
                    RAISE_APPLICATION_ERROR(-20001, 'Tenant mismatch between options and selections');
                END IF;
            END;
            """  # nosec

    def _log_model_processing(self) -> None:
        """Log information about the model being processed."""
        self.stdout.write(
            self.style.WARNING(
                "\nProcessing model: "
                f"'{self.context.model_name}' in app: '{self.context.app_label}' "
                f"with db_table: '{self.context.db_table}'"
            )
        )

    def _log_existing_trigger(self, migration_file: str) -> None:
        """Log information about an existing trigger.

        Args:
            migration_file: Path to the migration file containing the trigger
        """
        if self.verbose:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping trigger creation for model "
                    f"'{self.context.model_name}', which already exists at:\n\t{migration_file}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Trigger '{self.context.trigger_name}' for model '{self.context.model_name}' "
                    "already exists. Skipping..."
                )
            )

    def _log_trigger_sql_generation(self) -> None:
        """Log information about trigger SQL generation."""
        self.stdout.write(
            self.style.WARNING(
                f"Generating trigger SQL for model '{self.context.model_name}' with db_table "
                f"'{self.context.db_table}' and vendor '{self.db_vendor}'"
            )
        )

    def _trigger_exists(self) -> str | None:
        """Check if a trigger for the model already exists in any applied migration.

        Returns:
            Path to the migration file containing the trigger, or None if not found
        """
        migrations = MigrationRecorder.Migration.objects.filter(app=self.context.app_label).order_by("-applied")

        for migration in migrations:
            migration_file = (
                Path(apps.get_app_config(self.context.app_label).path) / "migrations" / f"{migration.name}.py"
            )

            if self.verbose:
                self.stdout.write(
                    self.style.WARNING(
                        f"Checking migration file for trigger {self.context.trigger_name}: {migration_file}"
                    )
                )

            if migration_file.exists():
                content = migration_file.read_text(encoding="utf-8")
                if self.context.trigger_name in content:
                    return str(migration_file)

        return None
