"""Test cases for model system checks (AbstractOption.check and AbstractSelection.check)."""

import pytest

from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import TaskStatusOption
from example_project.example.models import TaskStatusSelection


@pytest.mark.django_db
class TestOptionModelSystemChecks:
    """Test cases for AbstractOption.check() system checks."""

    def test_valid_option_model_no_errors(self):
        """Test that a valid Option model produces no errors or warnings."""
        errors = TaskPriorityOption.check()
        # Filter out only django_tenant_options errors/warnings
        dto_errors = [e for e in errors if e.id.startswith("django_tenant_options")]
        assert dto_errors == []

    def test_missing_unique_name_constraint(self, monkeypatch):
        """Test W007 warning when unique name constraint is missing."""
        original_constraints = TaskPriorityOption._meta.constraints[:]
        # Remove constraints to trigger warnings
        filtered = [c for c in original_constraints if "unique_name" not in getattr(c, "name", "")]
        monkeypatch.setattr(TaskPriorityOption._meta, "constraints", filtered)

        errors = TaskPriorityOption.check()
        w007 = [e for e in errors if e.id == "django_tenant_options.W007"]
        assert len(w007) == 1

    def test_missing_tenant_check_constraint(self, monkeypatch):
        """Test W008 warning when tenant check constraint is missing."""
        original_constraints = TaskPriorityOption._meta.constraints[:]
        filtered = [c for c in original_constraints if "tenant_check" not in getattr(c, "name", "")]
        monkeypatch.setattr(TaskPriorityOption._meta, "constraints", filtered)

        errors = TaskPriorityOption.check()
        w008 = [e for e in errors if e.id == "django_tenant_options.W008"]
        assert len(w008) == 1

    def test_missing_all_constraints(self, monkeypatch):
        """Test both W007 and W008 when all constraints are missing."""
        monkeypatch.setattr(TaskPriorityOption._meta, "constraints", [])

        errors = TaskPriorityOption.check()
        w007 = [e for e in errors if e.id == "django_tenant_options.W007"]
        w008 = [e for e in errors if e.id == "django_tenant_options.W008"]
        assert len(w007) == 1
        assert len(w008) == 1

    def test_another_option_model_valid(self):
        """Test that TaskStatusOption also passes checks."""
        errors = TaskStatusOption.check()
        dto_errors = [e for e in errors if e.id.startswith("django_tenant_options")]
        assert dto_errors == []


@pytest.mark.django_db
class TestSelectionModelSystemChecks:
    """Test cases for AbstractSelection.check() system checks."""

    def test_valid_selection_model_no_errors(self):
        """Test that a valid Selection model produces no errors or warnings."""
        errors = TaskPrioritySelection.check()
        dto_errors = [e for e in errors if e.id.startswith("django_tenant_options")]
        assert dto_errors == []

    def test_missing_option_not_null_constraint(self, monkeypatch):
        """Test W009 warning when option_not_null constraint is missing."""
        original_constraints = TaskPrioritySelection._meta.constraints[:]
        filtered = [c for c in original_constraints if "option_not_null" not in getattr(c, "name", "")]
        monkeypatch.setattr(TaskPrioritySelection._meta, "constraints", filtered)

        errors = TaskPrioritySelection.check()
        w009 = [e for e in errors if e.id == "django_tenant_options.W009"]
        assert len(w009) == 1

    def test_missing_tenant_not_null_constraint(self, monkeypatch):
        """Test W010 warning when tenant_not_null constraint is missing."""
        original_constraints = TaskPrioritySelection._meta.constraints[:]
        filtered = [c for c in original_constraints if "tenant_not_null" not in getattr(c, "name", "")]
        monkeypatch.setattr(TaskPrioritySelection._meta, "constraints", filtered)

        errors = TaskPrioritySelection.check()
        w010 = [e for e in errors if e.id == "django_tenant_options.W010"]
        assert len(w010) == 1

    def test_missing_unique_active_selection_constraint(self, monkeypatch):
        """Test W011 warning when unique_active_selection constraint is missing."""
        original_constraints = TaskPrioritySelection._meta.constraints[:]
        filtered = [c for c in original_constraints if "unique_active_selection" not in getattr(c, "name", "")]
        monkeypatch.setattr(TaskPrioritySelection._meta, "constraints", filtered)

        errors = TaskPrioritySelection.check()
        w011 = [e for e in errors if e.id == "django_tenant_options.W011"]
        assert len(w011) == 1

    def test_missing_all_selection_constraints(self, monkeypatch):
        """Test W009, W010, W011 when all constraints are missing."""
        monkeypatch.setattr(TaskPrioritySelection._meta, "constraints", [])

        errors = TaskPrioritySelection.check()
        w009 = [e for e in errors if e.id == "django_tenant_options.W009"]
        w010 = [e for e in errors if e.id == "django_tenant_options.W010"]
        w011 = [e for e in errors if e.id == "django_tenant_options.W011"]
        assert len(w009) == 1
        assert len(w010) == 1
        assert len(w011) == 1

    def test_another_selection_model_valid(self):
        """Test that TaskStatusSelection also passes checks."""
        errors = TaskStatusSelection.check()
        dto_errors = [e for e in errors if e.id.startswith("django_tenant_options")]
        assert dto_errors == []
