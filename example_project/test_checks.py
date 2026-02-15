"""Test cases for the checks module."""

from django.test import override_settings

from django_tenant_options.checks import check_manager_compliance
from django_tenant_options.models import OptionManager
from django_tenant_options.models import OptionQuerySet
from django_tenant_options.models import SelectionManager
from django_tenant_options.models import SelectionQuerySet
from example_project.example.models import TaskPriorityOption


class TestCheckManagerCompliance:
    """Test cases for the check_manager_compliance function."""

    @override_settings(DEBUG=False)
    def test_debug_false_skips_checks(self):
        """Test that checks are skipped when DEBUG is False."""
        results = check_manager_compliance(
            TaskPriorityOption,
            TaskPriorityOption.objects,
            OptionManager,
            OptionQuerySet,
            ("001", "002"),
        )
        assert results == []

    @override_settings(DEBUG=True)
    def test_valid_manager_and_queryset(self):
        """Test that a valid manager and queryset produce no issues."""
        results = check_manager_compliance(
            TaskPriorityOption,
            TaskPriorityOption.objects,
            OptionManager,
            OptionQuerySet,
            ("001", "002"),
        )
        assert results == []

    @override_settings(DEBUG=True)
    def test_invalid_manager_inheritance(self):
        """Test Warning when manager doesn't inherit from required manager."""
        from django.db import models

        class BadManager(models.Manager):
            pass

        bad_manager = BadManager()
        bad_manager.auto_created = True
        # Need to set _queryset_class
        bad_manager._queryset_class = models.QuerySet

        results = check_manager_compliance(
            TaskPriorityOption,
            bad_manager,
            OptionManager,
            OptionQuerySet,
            ("001", "002"),
        )
        assert len(results) == 1
        assert results[0].id == "django_tenant_options.I001"

    @override_settings(DEBUG=True)
    def test_valid_manager_invalid_queryset(self):
        """Test Error when manager inherits correctly but queryset doesn't."""
        from django.db import models

        class GoodManager(OptionManager):
            pass

        good_manager = GoodManager()
        # Override the queryset class to a non-compliant one
        good_manager._queryset_class = models.QuerySet

        results = check_manager_compliance(
            TaskPriorityOption,
            good_manager,
            OptionManager,
            OptionQuerySet,
            ("001", "002"),
        )
        assert len(results) == 1
        assert results[0].id == "django_tenant_options.E002"

    @override_settings(DEBUG=True)
    def test_selection_manager_compliance(self):
        """Test compliance check with SelectionManager/SelectionQuerySet."""
        from example_project.example.models import TaskPrioritySelection

        results = check_manager_compliance(
            TaskPrioritySelection,
            TaskPrioritySelection.objects,
            SelectionManager,
            SelectionQuerySet,
            ("004", "005"),
        )
        assert results == []
