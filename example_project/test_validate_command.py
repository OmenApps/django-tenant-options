"""Test cases for the validateoptions management command."""

from io import StringIO

import pytest
from django.core.management import call_command

from django_tenant_options.choices import OptionType
from django_tenant_options.models import OptionManager
from django_tenant_options.models import SelectionManager
from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import Tenant


CMD_MODULE = "django_tenant_options.management.commands.validateoptions"


@pytest.mark.django_db
class TestValidateOptionsCommand:
    """Test cases for the validateoptions management command."""

    def test_happy_path_valid_configuration(self):
        """Test that valid configuration produces success output."""
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "All validations passed!" in output

    def test_no_option_models_found(self, monkeypatch):
        """Test warning when no Option models are found."""
        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [])
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "No Option models found" in output

    def test_no_selection_models_found(self, monkeypatch):
        """Test warning when no Selection models are found."""
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "No Selection models found" in output

    def test_missing_objects_manager_on_option(self, monkeypatch):
        """Test error when Option model is missing 'objects' manager."""

        class FakeOptionModel:
            __name__ = "FakeOption"
            selection_model = "example.TaskPrioritySelection"
            tenant_model = "example.Tenant"
            default_options = {"Test": {"option_type": OptionType.MANDATORY}}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "Missing 'objects' manager" in output

    def test_invalid_manager_type_on_option(self, monkeypatch):
        """Test warning when Option model manager doesn't inherit from OptionManager."""
        from django.db import models

        class FakeManager(models.Manager):
            pass

        class FakeOptionModel:
            __name__ = "FakeOption"
            objects = FakeManager()
            selection_model = "example.TaskPrioritySelection"
            tenant_model = "example.Tenant"
            default_options = {"Test": {"option_type": OptionType.MANDATORY}}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "doesn't inherit from OptionManager" in output

    def test_missing_selection_model_attribute(self, monkeypatch):
        """Test error when Option model is missing selection_model."""

        class FakeOptionModel:
            __name__ = "FakeOption"
            objects = OptionManager()
            tenant_model = "example.Tenant"
            default_options = {"Test": {"option_type": OptionType.MANDATORY}}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "selection_model attribute not set" in output

    def test_missing_tenant_model_attribute(self, monkeypatch):
        """Test error when Option model is missing tenant_model."""

        class FakeOptionModel:
            __name__ = "FakeOption"
            objects = OptionManager()
            selection_model = "example.TaskPrioritySelection"
            default_options = {"Test": {"option_type": OptionType.MANDATORY}}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "tenant_model attribute not set" in output

    def test_invalid_option_type_in_default_options(self, monkeypatch):
        """Test error when default_options contains invalid option_type (e.g. CUSTOM)."""

        class FakeOptionModel:
            __name__ = "FakeOption"
            objects = OptionManager()
            selection_model = "example.TaskPrioritySelection"
            tenant_model = "example.Tenant"
            default_options = {"Bad": {"option_type": OptionType.CUSTOM}}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "Invalid option_type" in output

    def test_no_default_options_defined(self, monkeypatch):
        """Test warning when model has no default_options."""

        class FakeOptionModel:
            __name__ = "FakeOption"
            objects = OptionManager()
            selection_model = "example.TaskPrioritySelection"
            tenant_model = "example.Tenant"
            default_options = {}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "No default_options defined" in output

    def test_duplicate_names_in_database(self):
        """Test warning when duplicate default option names exist in database."""
        TaskPriorityOption.objects.create(name="DuplicateTest", option_type=OptionType.MANDATORY)
        opt2 = TaskPriorityOption.objects.create(name="DuplicateTest2", option_type=OptionType.MANDATORY)
        # Bypass validation to create duplicate name
        TaskPriorityOption.objects.filter(pk=opt2.pk).update(name="DuplicateTest")

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Duplicate default option names" in output

    def test_database_query_exception(self, monkeypatch):
        """Test warning when database query for duplicates raises an exception."""
        from django_tenant_options.management.commands.validateoptions import Command

        original_validate = Command._validate_option_model

        def patched_validate(self, model, errors, warnings):
            original_filter = model.objects.filter

            def failing_filter(*args, **kwargs):
                if "option_type__in" in kwargs:
                    raise Exception("DB connection failed")
                return original_filter(*args, **kwargs)

            monkeypatch.setattr(model.objects, "filter", failing_filter)
            original_validate(self, model, errors, warnings)

        monkeypatch.setattr(Command, "_validate_option_model", patched_validate)

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Could not check for duplicates" in output

    def test_missing_option_meta_constraints(self, monkeypatch):
        """Test warning when Option model is missing expected Meta constraints."""
        monkeypatch.setattr(TaskPriorityOption._meta, "constraints", [])

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Missing unique name constraint" in output
        assert "Missing tenant check constraint" in output

    def test_missing_selection_meta_constraints(self, monkeypatch):
        """Test warning when Selection model is missing expected Meta constraints."""
        monkeypatch.setattr(TaskPrioritySelection._meta, "constraints", [])

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Missing constraints" in output

    def test_selection_missing_option_model(self, monkeypatch):
        """Test error when Selection model is missing option_model."""

        class FakeSelectionModel:
            __name__ = "FakeSelection"
            objects = SelectionManager()
            tenant_model = "example.Tenant"
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeselection",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [FakeSelectionModel])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "option_model attribute not set" in output

    def test_selection_missing_tenant_model(self, monkeypatch):
        """Test error when Selection model is missing tenant_model."""

        class FakeSelectionModel:
            __name__ = "FakeSelection"
            objects = SelectionManager()
            option_model = "example.TaskPriorityOption"
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeselection",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [FakeSelectionModel])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "tenant_model attribute not set" in output

    def test_invalid_selection_manager_type(self, monkeypatch):
        """Test warning when Selection model manager doesn't inherit from SelectionManager."""
        from django.db import models

        class FakeManager(models.Manager):
            pass

        class FakeSelectionModel:
            __name__ = "FakeSelection"
            objects = FakeManager()
            option_model = "example.TaskPriorityOption"
            tenant_model = "example.Tenant"
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeselection",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [FakeSelectionModel])

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "doesn't inherit from SelectionManager" in output

    def test_orphaned_selections(self):
        """Test warning when active selections point to deleted options."""
        tenant = Tenant.objects.create(name="Test Tenant", subdomain="test-orphan")
        option = TaskPriorityOption.objects.create(
            name="Orphan Test Option", option_type=OptionType.CUSTOM, tenant=tenant
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=option)

        # Soft-delete the option directly to create an orphan
        from django.utils import timezone

        TaskPriorityOption.objects.filter(pk=option.pk).update(deleted=timezone.now())

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "active selection(s) pointing to deleted options" in output

    def test_orphaned_selections_query_exception(self, monkeypatch):
        """Test warning when orphaned selections query raises an exception."""
        from django_tenant_options.management.commands.validateoptions import Command

        original_validate = Command._validate_selection_model

        def patched_validate(self, model, errors, warnings):
            original_filter = model.objects.filter

            def failing_filter(*args, **kwargs):
                if "option__deleted__isnull" in kwargs:
                    raise Exception("DB error")
                return original_filter(*args, **kwargs)

            monkeypatch.setattr(model.objects, "filter", failing_filter)
            original_validate(self, model, errors, warnings)

        monkeypatch.setattr(Command, "_validate_selection_model", patched_validate)

        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Could not check for orphaned selections" in output

    def test_exit_code_1_on_errors(self, monkeypatch):
        """Test that the command exits with code 1 when errors are found."""

        class FakeOptionModel:
            __name__ = "FakeOption"
            selection_model = "example.TaskPrioritySelection"
            tenant_model = "example.Tenant"
            default_options = {}
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeoption",
                    "constraints": [],
                },
            )()

        # Missing objects manager will cause an error
        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [FakeOptionModel])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1

    def test_selection_missing_objects_manager(self, monkeypatch):
        """Test error when Selection model is missing 'objects' manager."""

        class FakeSelectionModel:
            __name__ = "FakeSelection"
            option_model = "example.TaskPriorityOption"
            tenant_model = "example.Tenant"
            _meta = type(
                "Meta",
                (),
                {
                    "app_label": "example",
                    "model_name": "fakeselection",
                    "constraints": [],
                },
            )()

        monkeypatch.setattr(f"{CMD_MODULE}.all_option_subclasses", lambda: [])
        monkeypatch.setattr(f"{CMD_MODULE}.all_selection_subclasses", lambda: [FakeSelectionModel])

        out = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("validateoptions", stdout=out)
        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "Missing 'objects' manager" in output

    def test_no_orphaned_selections_message(self):
        """Test that valid configuration shows 'No orphaned selections found'."""
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "No orphaned selections found" in output

    def test_option_model_count_displayed(self):
        """Test that the number of found Option models is displayed."""
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Found 2 Option model(s)" in output

    def test_selection_model_count_displayed(self):
        """Test that the number of found Selection models is displayed."""
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Found 2 Selection model(s)" in output

    def test_constraints_properly_configured_message(self):
        """Test that properly configured constraints are reported."""
        out = StringIO()
        call_command("validateoptions", stdout=out)
        output = out.getvalue()
        assert "Database constraints properly configured" in output
