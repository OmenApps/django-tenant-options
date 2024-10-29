"""Test cases for management commands with migration cleanup."""

from io import StringIO
from pathlib import Path

import pytest
from django.apps import apps
from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from example_project.example.models import TaskPriorityOption
from example_project.example.models import Tenant


@pytest.fixture
def deleted_priority():
    """Create a deleted priority option."""
    option = TaskPriorityOption.objects.create_optional(name="Deleted Priority")
    option.delete()
    return option


@pytest.fixture
def mock_migrations_dir(tmp_path):
    """Create a temporary migrations directory with mock migration files."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()

    # Create a mock migration file with trigger creation
    migration_content = """
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = []
    operations = [
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS example_taskpriorityselection_insert;',
            reverse_sql='',
        ),
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS example_taskpriorityselection_update;',
            reverse_sql='',
        ),
    ]
"""
    (migrations_dir / "0001_initial.py").write_text(migration_content)

    # Create a second migration file
    second_migration = """
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [('example', '0001_initial')]
    operations = [
        migrations.RunSQL(
            sql='DROP TRIGGER IF EXISTS example_taskpriorityselection_delete;',
            reverse_sql='',
        ),
    ]
"""
    (migrations_dir / "0002_additional.py").write_text(second_migration)
    return migrations_dir


@pytest.mark.django_db
class TestListOptionsCommand:
    """Test cases for the listoptions management command."""

    def test_listoptions_command(self):
        """Test the listoptions command."""
        out = StringIO()
        call_command("listoptions", stdout=out)
        output = out.getvalue()
        assert "Model: TaskPriorityOption" in output
        assert "Model: TaskStatusOption" in output

    def test_listoptions_with_deleted(self, deleted_priority):
        """Test the listoptions command does not show deleted options."""
        out = StringIO()
        call_command("listoptions", stdout=out)
        output = out.getvalue()
        assert deleted_priority.name not in output


@pytest.mark.django_db
class TestSyncOptionsCommand:
    """Test cases for the syncoptions management command."""

    @pytest.fixture
    def tenant(self):
        """Create a test tenant."""
        return Tenant.objects.create(name="Test Tenant", subdomain="test")

    @pytest.fixture
    def custom_priority(self, tenant):
        """Create a custom priority option."""
        return TaskPriorityOption.objects.create_for_tenant(tenant=tenant, name="Custom Priority")

    def test_syncoptions_command(self):
        """Test the syncoptions command."""
        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()
        assert "Model: TaskPriorityOption" in output
        assert "Model: TaskStatusOption" in output

    def test_syncoptions_with_new_defaults(self, monkeypatch):
        """Test syncoptions command updating new default options."""
        # Modify the default_options for testing
        new_defaults = {
            "New Priority": {"option_type": "do"},  # Default Optional
            "Critical": {"option_type": "dm"},  # Default Mandatory
        }
        monkeypatch.setattr(TaskPriorityOption, "default_options", new_defaults)

        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()

        # Verify output shows the imported options
        assert "New Priority" in output
        assert "Critical" in output
        assert "Imported or Verified Options" in output

        # Verify options were created in database
        assert TaskPriorityOption.objects.filter(name="New Priority").exists()
        assert TaskPriorityOption.objects.filter(name="Critical").exists()

    def test_syncoptions_delete_removed_defaults(self, monkeypatch):
        """Test syncoptions command handling removed default options."""
        # First create some default options
        TaskPriorityOption.objects.create_optional("Old Option")

        # Now set new defaults that don't include the old option
        monkeypatch.setattr(TaskPriorityOption, "default_options", {"New Option": {"option_type": "do"}})

        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()

        # Verify output shows the deleted options
        assert "Newly Deleted Options" in output
        assert "Old Option" in output

        # Verify the old option is now marked as deleted
        assert TaskPriorityOption.objects.deleted().filter(name="Old Option").exists()

    def test_syncoptions_with_custom_options(self, tenant, custom_priority):
        """Test syncoptions command handling custom options."""
        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()

        # Verify custom options are listed
        assert "All Custom Options" in output
        assert custom_priority.name in output
        assert str(tenant) in output

    def test_syncoptions_with_pre_existing_deleted(self, deleted_priority):
        """Test syncoptions command showing pre-existing deleted options."""
        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()

        # Verify pre-existing deleted options are listed
        assert "All Pre-existing Deleted Options" in output
        assert deleted_priority.name in output

    def test_syncoptions_empty_project(self, monkeypatch):
        """Test syncoptions command in a project with no options."""

        def mock_subclasses():
            return []

        monkeypatch.setattr("django_tenant_options.helpers.all_option_subclasses", mock_subclasses)

        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()
        assert "No default options found in the project." in output


@pytest.mark.django_db
class TestRemoveTriggersCommand:
    """Test cases for the removetriggers management command."""

    @pytest.fixture
    def command(self):
        """Create a Command instance for testing."""
        from django_tenant_options.management.commands.removetriggers import Command

        cmd = Command()
        cmd.stdout = StringIO()
        return cmd

    @pytest.fixture
    def command_options(self):
        """Default command options."""
        return {
            "app": None,
            "model": None,
            "dry_run": False,
            "migration_dir": None,
            "interactive": False,
            "verbose": False,
            "verify": False,
        }

    @pytest.fixture
    def mock_empty_migrations_dir(self, tmp_path):
        """Create an empty migrations directory."""
        migrations_dir = tmp_path / "empty_migrations"
        migrations_dir.mkdir()
        return migrations_dir

    def test_find_triggers_empty_directory(self, command, mock_empty_migrations_dir):
        """Test finding triggers in an empty migrations directory."""

        command.migration_dir = str(mock_empty_migrations_dir)
        triggers = command._find_triggers_for_model("example", "TaskPrioritySelection")

        assert len(triggers) == 0

    def test_initialize_options(self, command):
        """Test initialization of command options."""

        options = {
            "app": "example",
            "model": "example.TaskPrioritySelection",
            "dry_run": True,
            "migration_dir": "/test/path",
            "interactive": True,
            "verbose": True,
            "verify": True,
        }

        command._initialize_options(options)

        assert command.app_label == "example"
        assert command.model_name == "example.TaskPrioritySelection"
        assert command.dry_run is True
        assert command.migration_dir == "/test/path"
        assert command.interactive is True
        assert command.verbose is True
        assert command.verify is True

    def test_migration_content_generation(self, command, mock_migrations_dir):
        """Test generation of migration file content."""
        from django_tenant_options.management.commands.removetriggers import TriggerInfo

        triggers = {
            TriggerInfo(
                trigger_name="test_trigger",
                migration_file=Path("test_migration.py"),
                model_name="TestModel",
                app_label="example",
            )
        }

        content = command._generate_migration_content("example", triggers)

        # Check essential parts of the migration content
        assert "from django.db import migrations" in content
        assert "class Migration(migrations.Migration):" in content
        assert "dependencies = [" in content
        assert "operations = [" in content
        assert "DROP TRIGGER IF EXISTS test_trigger" in content
        assert "reverse_sql=''" in content  # Check for empty reverse SQL

    def test_process_triggers_no_triggers(self, command):
        """Test processing when no triggers are found."""

        out = StringIO()
        command.stdout = out

        command._process_triggers([])
        assert "No triggers found to remove" in out.getvalue()

    def test_handle_interactive_rejection(self, monkeypatch):
        """Test interactive mode when user rejects the operation."""
        out = StringIO()

        # Mock user input to reject
        monkeypatch.setattr("builtins.input", lambda _: "n")

        call_command("removetriggers", interactive=True, stdout=out)
        output = out.getvalue()

        # Should not see success message
        assert "Created migration" not in output

    def test_get_migrations_dir(self, command, tmp_path):
        """Test getting migrations directory with custom path."""

        custom_path = tmp_path / "custom_migrations"
        command.migration_dir = str(custom_path)

        result = command._get_migrations_dir("example")
        assert result == custom_path

    @pytest.mark.django_db
    def test_handle_verify_mode_with_existing_migrations(self, mock_migrations_dir):
        """Test verify mode with existing migrations in the database."""
        # Create a test migration record
        MigrationRecorder.Migration.objects.create(app="example", name="0001_initial", applied=timezone.now())

        out = StringIO()
        call_command(
            "removetriggers",
            verify=True,
            model="example.TaskPrioritySelection",
            migration_dir=str(mock_migrations_dir),
            stdout=out,
        )
        output = out.getvalue()

        # Command should attempt to process triggers
        assert len(output) > 0

    def test_create_removal_migration_dry_run_verbose(self, command, mock_migrations_dir):
        """Test creation of removal migration in dry run mode with verbose output."""
        from django_tenant_options.management.commands.removetriggers import TriggerInfo

        command.dry_run = True
        command.verbose = True
        out = StringIO()
        command.stdout = out

        triggers = {
            TriggerInfo(
                trigger_name="test_trigger",
                migration_file=Path("test_migration.py"),
                model_name="TestModel",
                app_label="example",
            )
        }

        command._create_removal_migration("example", triggers)
        output = out.getvalue()

        assert "[DRY RUN]" in output
        assert "Would remove triggers: test_trigger" in output

    def test_non_abstract_selection_models(self, command):
        """Test handling of non-AbstractSelection models."""

        out = StringIO()
        command.stdout = out

        # Try to process a model that isn't a subclass of AbstractSelection
        command._handle_single_model("auth", "User")

        assert "is not a subclass of AbstractSelection" in out.getvalue()

    @pytest.mark.django_db
    def test_migration_dependencies_handling(self, command, mock_migrations_dir):
        """Test proper handling of migration dependencies."""
        # Create some test migrations in the database
        MigrationRecorder.Migration.objects.create(app="example", name="0001_initial", applied=timezone.now())
        MigrationRecorder.Migration.objects.create(app="example", name="0002_additional", applied=timezone.now())

        name = command._construct_migration_name("example")

        # Should be "0003" since we have two existing migrations
        assert name.startswith("0003")

    def test_generate_migration_no_previous_migration(self, command):
        """Test migration generation when no previous migrations exist."""

        name = command._construct_migration_name("example")

        # If no migrations exist, should still get a valid name
        assert "remove_triggers" in name

    def test_handle_dry_run(self, command, mock_migrations_dir):
        """Test dry run mode."""

        command.migration_dir = str(mock_migrations_dir)
        command.dry_run = True
        command.verbose = True

        out = StringIO()
        command.stdout = out

        # Force the command to find triggers
        command._handle_single_model("example", "TaskPrioritySelection")
        output = out.getvalue()

        assert "No triggers found to remove" in output or "[DRY RUN]" in output

    def test_verbose_output(self):
        """Test verbose output mode."""
        out = StringIO()
        call_command("removetriggers", verbose=True, stdout=out)
        output = out.getvalue()

        assert len(output) > 0  # Verbose should produce more output

    def test_verify_mode(self, command, mock_migrations_dir):
        """Test verify mode."""

        command.migration_dir = str(mock_migrations_dir)
        command.verify = True
        out = StringIO()
        command.stdout = out

        # Force the command to find triggers
        command._handle_single_model("example", "TaskPrioritySelection")

        assert len(out.getvalue()) > 0

    def test_trigger_info_equality(self):
        """Test TriggerInfo equality comparison."""
        from django_tenant_options.management.commands.removetriggers import TriggerInfo

        trigger1 = TriggerInfo("trigger1", Path("migration1.py"), "Model1", "example")
        trigger2 = TriggerInfo("trigger1", Path("migration1.py"), "Model1", "example")
        trigger3 = TriggerInfo("trigger2", Path("migration1.py"), "Model1", "example")

        assert trigger1 == trigger2
        assert trigger1 != trigger3
        assert hash(trigger1) == hash(trigger2)
        assert hash(trigger1) != hash(trigger3)

    def test_migration_path_generation(self, command, tmp_path):
        """Test migration path generation."""

        command.migration_dir = str(tmp_path)
        path = command._get_migration_path("example", "0002_remove_triggers")

        assert isinstance(path, Path)
        assert path.parent == tmp_path
        assert path.name == "0002_remove_triggers.py"

    def test_migration_name_construction(self, command):
        """Test migration name construction."""

        name = command._construct_migration_name("example")

        assert name.endswith("_remove_triggers")
        assert name.split("_")[0].isdigit()

    def test_invalid_app_label(self):
        """Test handling of invalid app label."""
        with pytest.raises(LookupError):
            call_command("removetriggers", app="nonexistent_app")

    def test_invalid_model_name(self):
        """Test handling of invalid model name."""
        with pytest.raises(LookupError):
            call_command("removetriggers", model="example.NonexistentModel")

    def test_custom_migration_directory(self, tmp_path):
        """Test using custom migration directory."""
        custom_dir = tmp_path / "custom_migrations"
        custom_dir.mkdir()

        out = StringIO()
        call_command("removetriggers", migration_dir=str(custom_dir), stdout=out)

        assert custom_dir.exists()
        assert list(custom_dir.glob("*.py")) == []  # No migrations should be created in dry run


@pytest.mark.django_db
class TestMakeTriggersCommand:
    """Test suite for the maketriggers management command."""

    @pytest.fixture
    def command(self):
        """Create a Command instance for testing."""
        from django_tenant_options.management.commands.maketriggers import Command

        cmd = Command()
        cmd.stdout = StringIO()
        return cmd

    @pytest.fixture
    def mock_context(self, command):
        """Create a mock context for the command."""

        class MockContext:
            """Mock context for the command."""

            trigger_name = "test_trigger"
            db_table = "test_table"
            model_name = "test_model"
            app_label = "test_app"

        command.context = MockContext()
        return command.context

    def test_maketriggers_command(self):
        """Test the maketriggers command."""
        out = StringIO()
        call_command("maketriggers", stdout=out)
        output = out.getvalue()
        assert "Creating migration for taskpriorityselection" in output

    def test_confirm_creation(self, command, mock_context, monkeypatch):
        """Test _confirm_creation with yes/no responses."""
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert command._confirm_creation() is True

        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert command._confirm_creation() is False

    def test_get_trigger_sql_for_vendors(self, command, mock_context):
        """Test trigger SQL generation for different database vendors."""
        # Test PostgreSQL trigger
        command.db_vendor = "postgresql"
        postgresql_sql = command._get_trigger_sql()
        assert "CREATE OR REPLACE FUNCTION" in postgresql_sql
        assert "RETURNS TRIGGER" in postgresql_sql
        assert "test_trigger" in postgresql_sql
        assert "test_table" in postgresql_sql

        # Test MySQL trigger
        command.db_vendor = "mysql"
        mysql_sql = command._get_trigger_sql()
        assert "CREATE TRIGGER" in mysql_sql
        assert "BEFORE INSERT" in mysql_sql
        assert "test_trigger" in mysql_sql
        assert "test_table" in mysql_sql

        # Test Oracle trigger
        command.db_vendor = "oracle"
        oracle_sql = command._get_trigger_sql()
        assert "CREATE OR REPLACE TRIGGER" in oracle_sql
        assert "BEFORE INSERT" in oracle_sql
        assert "test_trigger" in oracle_sql
        assert "test_table" in oracle_sql

    def test_handle_app_models(self, command, monkeypatch):
        """Test handling of app models."""
        from django_tenant_options.management.commands.maketriggers import Command

        process_called = []

        def mock_process_app_models(self, app_config):
            """Mock method to append processed app models."""
            process_called.append(app_config)

        monkeypatch.setattr(Command, "_process_app_models", mock_process_app_models)
        command._handle_app_models("example")

        assert len(process_called) == 1
        assert process_called[0] == apps.get_app_config("example")

    def test_handle_dry_run(self, command, mock_context, monkeypatch):
        """Test dry run handling."""
        from django_tenant_options.management.commands.maketriggers import Command

        migration_path = Path("/test/path/migration.py")
        command.verbose = True

        def mock_get_migration_content(self, last_migration):
            """Mock method to return migration content."""
            return "Migration content"

        monkeypatch.setattr(Command, "_get_migration_content", mock_get_migration_content)
        command._handle_dry_run(migration_path)

        output = command.stdout.getvalue()
        assert "[DRY RUN] Migration would be created:" in output
        assert "Migration content" in output

    def test_handle_single_model(self, mock_migrations_dir):
        """Test handling of a single model."""
        out = StringIO()
        call_command(
            "removetriggers", model="example.TaskPrioritySelection", migration_dir=str(mock_migrations_dir), stdout=out
        )
        output = out.getvalue()

        # Should process the model
        assert len(output) > 0

    def test_log_existing_trigger(self, command, mock_context):
        """Test logging of existing triggers."""
        # Test verbose output
        command.verbose = True
        command._log_existing_trigger("path/to/migration.py")
        output = command.stdout.getvalue()
        assert "Skipping trigger creation for model" in output
        assert "path/to/migration.py" in output

        # Test non-verbose output
        command.stdout = StringIO()  # Reset output
        command.verbose = False
        command._log_existing_trigger("path/to/migration.py")
        output = command.stdout.getvalue()
        assert "Trigger 'test_trigger' for model 'test_model' already exists" in output

    def test_log_model_processing(self, command, mock_context):
        """Test logging of model processing."""
        command._log_model_processing()
        output = command.stdout.getvalue()
        assert "Processing model: 'test_model'" in output
        assert "test_app" in output
        assert "test_table" in output

    def test_log_trigger_sql_generation(self, command, mock_context):
        """Test logging of trigger SQL generation."""
        command.db_vendor = "postgresql"

        command._log_trigger_sql_generation()
        output = command.stdout.getvalue()
        assert "Generating trigger SQL for model 'test_model'" in output
        assert "postgresql" in output

    def test_process_app_models(self, command, monkeypatch):
        """Test processing of app models."""
        from django_tenant_options.management.commands.maketriggers import Command

        processed_models = []

        def mock_should_process_model(cls, model):
            """Mock method to always return True."""
            return True

        def mock_process_model(self, model):
            """Mock method to append processed models."""
            processed_models.append(model)

        monkeypatch.setattr(Command, "_should_process_model", classmethod(mock_should_process_model))
        monkeypatch.setattr(Command, "_process_model", mock_process_model)

        app_config = apps.get_app_config("example")
        command._process_app_models(app_config)

        # Verify _process_model was called for models in the app
        assert len(processed_models) > 0

    def test_get_mysql_trigger(self, command, mock_context):
        """Test MySQL trigger SQL generation."""
        sql = command._get_mysql_trigger()
        assert "CREATE TRIGGER" in sql
        assert "test_trigger" in sql
        assert "test_table" in sql
        assert "BEFORE INSERT" in sql
        assert "SIGNAL SQLSTATE '45000'" in sql

    def test_get_oracle_trigger(self, command, mock_context):
        """Test Oracle trigger SQL generation."""
        sql = command._get_oracle_trigger()
        assert "CREATE OR REPLACE TRIGGER" in sql
        assert "test_trigger" in sql
        assert "test_table" in sql
        assert "BEFORE INSERT" in sql
        assert "RAISE_APPLICATION_ERROR" in sql

    def test_get_postgresql_trigger(self, command, mock_context):
        """Test PostgreSQL trigger SQL generation."""
        sql = command._get_postgresql_trigger()
        assert "CREATE OR REPLACE FUNCTION" in sql
        assert "test_trigger" in sql
        assert "test_table" in sql
        assert "RETURNS TRIGGER" in sql
        assert "LANGUAGE plpgsql" in sql
