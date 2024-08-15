"""Management command to generate migrations with triggers for models subclassed from AbstractSelection."""

import hashlib
import os
import re
from argparse import RawTextHelpFormatter
from datetime import datetime
from textwrap import dedent

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from django_tenant_options.app_settings import DB_VENDOR_OVERRIDE
from django_tenant_options.models import AbstractSelection


class Command(BaseCommand):
    """Management command to generate migrations with triggers for models subclassed from AbstractSelection."""

    help = dedent(
        """\
    Generate migrations with triggers for models subclassed from AbstractSelection.

    These triggers ensure there can never be mismatch between a Tenant and an associated Option.

    Note: This command always drops any existing trigger before creating a new one, so forcing the creation of
    migrations will not cause an OperationalError.
    """
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_label = None
        self.model_name = None
        self.db_table = None
        self.force = False
        self.dry_run = False
        self.migration_dir = None
        self.interactive = False
        self.verbose = False
        self.last_generated_migration = None
        self.trigger_name = None
        self.db_vendor = None

    def create_parser(self, *args, **kwargs):
        """Create a parser with RawTextHelpFormatter to preserve newlines in help text."""
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        self.app_label = options.get("app")
        self.model_name = options.get("model")
        self.force = options.get("force")
        self.dry_run = options.get("dry_run")
        self.migration_dir = options.get("migration_dir")
        self.interactive = options.get("interactive")
        self.verbose = options.get("verbose")
        self.last_generated_migration = None

        self.db_vendor = options.get("db_vendor_override") or DB_VENDOR_OVERRIDE or connection.vendor

        if self.model_name:
            self.app_label, model_name = self.model_name.split(".")
            model = apps.get_model(self.app_label, model_name)
            self.last_generated_migration = self.create_migration_for_model(model)
        elif self.app_label:
            for model in apps.get_app_config(self.app_label).get_models():
                if issubclass(model, AbstractSelection) and model != AbstractSelection:
                    self.last_generated_migration = self.create_migration_for_model(model)
        else:
            for model in apps.get_models():
                if issubclass(model, AbstractSelection) and model != AbstractSelection:
                    self.last_generated_migration = self.create_migration_for_model(model)

    def create_migration_for_model(self, model):
        """Create a migration file for the given model."""
        self.app_label = model._meta.app_label  # pylint: disable=W0212
        self.db_table = model._meta.db_table  # pylint: disable=W0212
        self.model_name = model.__name__.lower()
        self.trigger_name = self.construct_trigger_name()

        if self.verbose:
            self.stdout.write(
                self.style.WARNING(  # pylint: disable=E1101
                    "\nProcessing model: "
                    f"'{self.model_name}' in app: '{self.app_label}' with db_table: '{self.db_table}'"
                )
            )

        if not self.force and (migration_file := self.trigger_exists()):
            if self.verbose:
                self.stdout.write(
                    self.style.WARNING(  # pylint: disable=E1101
                        "Skipping trigger creation for model "
                        f"'{self.model_name}', which already exists at:\n\t{migration_file}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(  # pylint: disable=E1101
                        f"Trigger '{self.trigger_name}' for model '{self.model_name}' already exists. Skipping..."
                    )
                )
            return self.last_generated_migration

        last_migration = self.get_last_migration_name()
        migration_name = self.construct_migration_name(last_migration)
        trigger_sql = self.get_trigger_sql()
        migration_file_path = self.get_migration_file_path(migration_name)

        if self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(  # pylint: disable=E1101
                    f"[DRY RUN] Migration would be created: {migration_file_path}"
                )
            )
            if self.verbose:
                self.stdout.write(
                    "[DRY RUN] Migration content:\n" f"{self.get_migration_template(last_migration, trigger_sql)}"
                )
        else:
            if self.interactive:
                confirm = input(f"Do you want to create a migration for {self.model_name}? (y/n): ")
                if confirm.lower() != "y":
                    self.stdout.write(
                        self.style.WARNING(  # pylint: disable=E1101
                            f"Migration creation for {self.model_name} skipped by user."
                        )
                    )
                    return self.last_generated_migration

            self.stdout.write(
                self.style.WARNING(f"Creating migration for {self.model_name}...")  # pylint: disable=E1101
            )
            self.write_migration_file(migration_file_path, last_migration, trigger_sql)
            self.stdout.write(self.style.SUCCESS(f"Migration created: {migration_file_path}"))  # pylint: disable=E1101

        return migration_name

    def trigger_exists(self):
        """Check if a trigger for the model already exists in any applied migration."""
        migrations = MigrationRecorder.Migration.objects.filter(app=self.app_label).order_by(  # pylint: disable=E1101
            "-applied"
        )
        for migration in migrations:
            migration_file = os.path.join(
                apps.get_app_config(self.app_label).path,
                "migrations",
                f"{migration.name}.py",
            )
            if self.verbose:
                self.stdout.write(
                    self.style.WARNING(  # pylint: disable=E1101
                        f"Checking migration file for trigger {self.trigger_name}: {migration_file}"
                    )
                )
            if os.path.exists(migration_file):
                with open(migration_file, "r", encoding="utf-8") as file:
                    content = file.read()
                    if f"{self.trigger_name}" in content:
                        return migration_file
        return False

    def get_last_migration_name(self):
        """Retrieve the last migration name or use the previously generated one."""
        if self.last_generated_migration:
            return self.last_generated_migration
        last_migration = MigrationRecorder.Migration.objects.filter(app=self.app_label).last()  # pylint: disable=E1101
        return last_migration.name if last_migration else None

    def construct_trigger_name(self):
        """Construct the trigger name based on the model's db_table.

        Result generally looks like: <db_table>_tenant_check_<hash>
        """
        max_identifier_length = connection.ops.max_name_length() or 200
        table_name = self.db_table.replace('"', "").replace(".", "_") + "_tenant_check"  # pylint: disable=W0212
        hashed_table_name = hashlib.sha1(table_name.encode("utf-8")).hexdigest()[:10]
        trigger_hash = f"_{hashed_table_name}"
        hash_length = len(trigger_hash)

        if self.verbose:
            self.stdout.write(
                self.style.WARNING(  # pylint: disable=E1101
                    "Creating hash for trigger name: "
                    f"{max_identifier_length=}, {table_name=}, {trigger_hash=}, {hash_length=}"
                )
            )

        # Name shouldn't start with an underscore or digit. If it does, prepend with 't'.
        if table_name[0] == "_" or table_name[0].isdigit():
            table_name = f"t{table_name[:-1]}"

        trigger_name = f"{table_name[:max_identifier_length - hash_length]}{trigger_hash}"
        if self.verbose:
            self.stdout.write(
                self.style.WARNING(  # pylint: disable=E1101
                    f"Constructed trigger name for model '{self.model_name}': {trigger_name}"
                )
            )

        return trigger_name

    def construct_migration_name(self, last_migration):
        """Construct the migration name based on the last migration."""
        match = re.match(r"^(\d+)_", last_migration)
        if match:
            new_migration_number = str(int(match.group(1)) + 1).zfill(4)
            return f"{new_migration_number}_auto_trigger_{self.model_name}"
        migration_name = f"auto_trigger_{self.model_name}"
        if self.verbose:
            self.stdout.write(
                self.style.WARNING(  # pylint: disable=E1101
                    f"Constructed migration name for model '{self.model_name}': {migration_name}"
                )
            )

        return migration_name

    def get_migration_file_path(self, migration_name):
        """Determine the correct path for the migration file."""
        app_config = apps.get_app_config(self.app_label)
        migrations_dir = self.migration_dir if self.migration_dir else os.path.join(app_config.path, "migrations")

        if not os.path.exists(migrations_dir):
            os.makedirs(migrations_dir)

        return os.path.join(migrations_dir, f"{migration_name}.py")

    def write_migration_file(self, file_path, last_migration, trigger_sql):
        """Write the migration file to the specified path."""
        migration_content = self.get_migration_template(last_migration, trigger_sql)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(migration_content)

    def get_trigger_sql(self):
        """Return the SQL for creating the trigger."""
        if self.verbose:
            self.stdout.write(
                self.style.WARNING(  # pylint: disable=E1101
                    f"Generating trigger SQL for model '{self.model_name}' with db_table "
                    f"'{self.db_table}' and vendor '{self.db_vendor}'"
                )
            )
        if self.db_vendor == "sqlite":
            return f"""
            DROP TRIGGER IF EXISTS {self.trigger_name};
            CREATE TRIGGER {self.trigger_name}
            BEFORE INSERT ON {self.db_table}
            FOR EACH ROW
            WHEN NEW.tenant_id != (SELECT tenant_id FROM {self.db_table} WHERE id = NEW.option_id)
            BEGIN
                SELECT RAISE(FAIL, 'Tenant mismatch between {self.db_table} and the associated Option');
            END;
            """
        elif self.db_vendor == "postgresql":
            return f"""
            CREATE OR REPLACE FUNCTION {self.trigger_name}()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.tenant_id != (SELECT tenant_id FROM {self.db_table} WHERE id = NEW.option_id) THEN
                    RAISE EXCEPTION 'Tenant mismatch between {self.db_table} and the associated Option';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS {self.trigger_name} ON {self.db_table};
            CREATE TRIGGER {self.trigger_name}
            BEFORE INSERT ON {self.db_table}
            FOR EACH ROW
            EXECUTE FUNCTION {self.trigger_name}();
            """
        elif self.db_vendor == "mysql":
            return f"""
            DROP TRIGGER IF EXISTS {self.trigger_name};
            CREATE TRIGGER {self.trigger_name}
            BEFORE INSERT ON {self.db_table}
            FOR EACH ROW
            BEGIN
                DECLARE option_tenant_id INT;
                SELECT tenant_id INTO option_tenant_id FROM {self.db_table} WHERE id = NEW.option_id;

                IF NEW.tenant_id != option_tenant_id THEN
                    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tenant mismatch between {self.db_table} and the associated Option';
                END IF;
            END;
            """
        elif self.db_vendor == "oracle":
            return f"""
            CREATE OR REPLACE TRIGGER {self.trigger_name}
            BEFORE INSERT ON {self.db_table}
            FOR EACH ROW
            DECLARE
                option_tenant_id NUMBER;
            BEGIN
                SELECT tenant_id INTO option_tenant_id FROM {self.db_table} WHERE id = :NEW.option_id;

                IF :NEW.tenant_id != option_tenant_id THEN
                    RAISE_APPLICATION_ERROR(-20001, 'Tenant mismatch between {self.db_table} and the associated Option');
                END IF;
            END;
            """
        else:
            raise ValueError(f"Unsupported database backend: {self.db_vendor}")

    def get_migration_template(self, last_migration, trigger_sql):
        """Return the migration template."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return dedent(
            f"""\
        # Generated by django-tenant-options on {timestamp}

        from django.db import migrations


        class Migration(migrations.Migration):
            \"\"\"Adds an auto-generated trigger for a django-tenant-options Selection model.\"\"\"

            dependencies = [
                ('{self.app_label}', '{last_migration}'),
            ]

            operations = [
                migrations.RunSQL(
                    sql=\"\"\"{trigger_sql}\"\"\",
                    reverse_sql=\"\"\"DROP TRIGGER IF EXISTS {self.trigger_name};\"\"\",
                ),
            ]
        """
        )
