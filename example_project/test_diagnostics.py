"""Test cases for the django_tenant_options.diagnostics module."""

import pytest

from django_tenant_options.choices import OptionType
from django_tenant_options.diagnostics import DiagnosticsResult
from django_tenant_options.diagnostics import check_option_model
from django_tenant_options.diagnostics import check_selection_model
from django_tenant_options.diagnostics import run_diagnostics
from django_tenant_options.models import OptionManager
from django_tenant_options.models import SelectionManager


class TestDiagnosticsResult:
    """Test cases for the DiagnosticsResult dataclass."""

    def test_defaults_to_empty_lists(self):
        """A fresh result has empty errors, warnings, and infos."""
        result = DiagnosticsResult()
        assert result.errors == []
        assert result.warnings == []
        assert result.infos == []

    def test_lists_are_independent_between_instances(self):
        """Mutating one instance does not affect another (no shared mutable default)."""
        first = DiagnosticsResult()
        second = DiagnosticsResult()
        first.errors.append("boom")
        assert second.errors == []

    def test_has_errors_property(self):
        """has_errors is True only when errors are present."""
        result = DiagnosticsResult()
        assert result.has_errors is False
        result.errors.append("boom")
        assert result.has_errors is True

    def test_has_warnings_property(self):
        """has_warnings is True only when warnings are present."""
        result = DiagnosticsResult()
        assert result.has_warnings is False
        result.warnings.append("careful")
        assert result.has_warnings is True

    def test_passed_count(self):
        """passed_count returns the number of info (passed-check) lines."""
        result = DiagnosticsResult()
        assert result.passed_count == 0
        result.infos.append("ok")
        result.infos.append("ok2")
        assert result.passed_count == 2


@pytest.mark.django_db
class TestCheckOptionModel:
    """Test cases for check_option_model."""

    def _make_fake(self, **overrides):
        """Build a minimal fake Option model with overridable attributes."""
        attrs = {
            "__name__": "FakeOption",
            "objects": OptionManager(),
            "selection_model": "example.TaskPrioritySelection",
            "tenant_model": "example.Tenant",
            "default_options": {"Test": {"option_type": OptionType.MANDATORY}},
            "_meta": type(
                "Meta",
                (),
                {"app_label": "example", "model_name": "fakeoption", "constraints": []},
            )(),
        }
        attrs.update(overrides)
        return type("FakeOption", (), attrs)

    def test_missing_objects_manager_is_error(self):
        """A model with no objects manager produces an error."""
        model = self._make_fake()
        del model.objects
        result = DiagnosticsResult()
        check_option_model(model, result)
        assert any("Missing 'objects' manager" in e for e in result.errors)

    def test_missing_selection_model_is_error(self):
        """A model with no selection_model produces an error."""
        model = self._make_fake(selection_model=None)
        result = DiagnosticsResult()
        check_option_model(model, result)
        assert any("selection_model attribute not set" in e for e in result.errors)

    def test_missing_tenant_model_is_error(self):
        """A model with no tenant_model produces an error."""
        model = self._make_fake(tenant_model=None)
        result = DiagnosticsResult()
        check_option_model(model, result)
        assert any("tenant_model attribute not set" in e for e in result.errors)

    def test_invalid_default_option_type_is_error(self):
        """A CUSTOM option_type in default_options produces an error."""
        model = self._make_fake(default_options={"Bad": {"option_type": OptionType.CUSTOM}})
        result = DiagnosticsResult()
        check_option_model(model, result)
        assert any("Invalid option_type" in e for e in result.errors)

    def test_no_default_options_is_warning(self):
        """An empty default_options dict produces a warning."""
        model = self._make_fake(default_options={})
        result = DiagnosticsResult()
        check_option_model(model, result)
        assert any("No default_options defined" in w for w in result.warnings)

    def test_manager_configured_is_info(self):
        """A model with a proper manager records a 'manager configured' info line."""
        model = self._make_fake()
        result = DiagnosticsResult()
        check_option_model(model, result)
        assert any("manager configured" in i.lower() for i in result.infos)


@pytest.mark.django_db
class TestCheckSelectionModel:
    """Test cases for check_selection_model."""

    def _make_fake(self, **overrides):
        """Build a minimal fake Selection model with overridable attributes."""
        attrs = {
            "__name__": "FakeSelection",
            "objects": SelectionManager(),
            "option_model": "example.TaskPriorityOption",
            "tenant_model": "example.Tenant",
            "_meta": type(
                "Meta",
                (),
                {"app_label": "example", "model_name": "fakeselection", "constraints": []},
            )(),
        }
        attrs.update(overrides)
        return type("FakeSelection", (), attrs)

    def test_missing_objects_manager_is_error(self):
        """A model with no objects manager produces an error."""
        model = self._make_fake()
        del model.objects
        result = DiagnosticsResult()
        check_selection_model(model, result)
        assert any("Missing 'objects' manager" in e for e in result.errors)

    def test_missing_option_model_is_error(self):
        """A model with no option_model produces an error."""
        model = self._make_fake(option_model=None)
        result = DiagnosticsResult()
        check_selection_model(model, result)
        assert any("option_model attribute not set" in e for e in result.errors)

    def test_missing_tenant_model_is_error(self):
        """A model with no tenant_model produces an error."""
        model = self._make_fake(tenant_model=None)
        result = DiagnosticsResult()
        check_selection_model(model, result)
        assert any("tenant_model attribute not set" in e for e in result.errors)

    def test_invalid_manager_type_is_warning(self):
        """A non-SelectionManager objects manager produces a warning."""
        from django.db import models

        class FakeManager(models.Manager):
            pass

        model = self._make_fake(objects=FakeManager())
        result = DiagnosticsResult()
        check_selection_model(model, result)
        assert any("doesn't inherit from SelectionManager" in w for w in result.warnings)


@pytest.mark.django_db
class TestRunDiagnostics:
    """Test cases for run_diagnostics."""

    def test_valid_example_config_has_no_errors(self):
        """The example project's real models produce zero errors."""
        result = run_diagnostics()
        assert result.errors == []

    def test_valid_example_config_has_passed_checks(self):
        """The example project's real models produce info (passed) lines."""
        result = run_diagnostics()
        assert result.passed_count > 0

    def test_no_option_models_warns(self, monkeypatch):
        """A warning is recorded when no Option models exist."""
        monkeypatch.setattr("django_tenant_options.diagnostics.all_option_subclasses", lambda: [])
        result = run_diagnostics()
        assert any("No Option models found" in w for w in result.warnings)

    def test_no_selection_models_warns(self, monkeypatch):
        """A warning is recorded when no Selection models exist."""
        monkeypatch.setattr("django_tenant_options.diagnostics.all_selection_subclasses", lambda: [])
        result = run_diagnostics()
        assert any("No Selection models found" in w for w in result.warnings)

    def test_orphaned_selection_produces_warning(self):
        """A soft-deleted option behind an active selection warns."""
        from django.utils import timezone

        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="Orphan T", subdomain="orphan-diag")
        option = TaskPriorityOption.objects.create(
            name="Orphan Diag Option", option_type=OptionType.CUSTOM, tenant=tenant
        )
        TaskPrioritySelection.objects.create(tenant=tenant, option=option)
        TaskPriorityOption.objects.filter(pk=option.pk).update(deleted=timezone.now())

        result = run_diagnostics()
        assert any("active selection(s) pointing to deleted options" in w for w in result.warnings)
