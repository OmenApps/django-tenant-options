"""Test cases for management commands with migration cleanup."""

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestManagementCommands:
    """Test cases for the management commands."""

    def test_listoptions_command(self):
        """Test the listoptions command."""
        out = StringIO()
        call_command("listoptions", stdout=out)
        output = out.getvalue()
        assert "Model: TaskPriorityOption" in output
        assert "Model: TaskStatusOption" in output

    def test_syncoptions_command(self):
        """Test the syncoptions command."""
        out = StringIO()
        call_command("syncoptions", stdout=out)
        output = out.getvalue()
        assert "Model: TaskPriorityOption" in output
        assert "Model: TaskStatusOption" in output

    def test_maketriggers_command(self):
        """Test the maketriggers command."""
        out = StringIO()
        call_command("maketriggers", stdout=out)
        output = out.getvalue()
        assert "Creating migration for taskpriorityselection" in output
