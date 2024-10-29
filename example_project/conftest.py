"""Pytest configuration for example project."""

from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class MigrationTracker:
    """Tracks migration files created during tests."""

    def __init__(self):
        """Initialize MigrationTracker."""
        self.initial_migrations = set()

    def snapshot_migrations(self):
        """Take a snapshot of existing migration files."""
        self.initial_migrations.clear()
        for app_config in settings.INSTALLED_APPS:
            if "." in app_config:
                app_name = app_config.split(".")[-1]
                migrations_dir = Path(settings.BASE_DIR) / "example_project" / app_name / "migrations"
                if migrations_dir.exists():
                    self.initial_migrations.update(str(f.absolute()) for f in migrations_dir.glob("[0-9]*.py"))

    def get_new_migrations(self):
        """Get list of migration files created since last snapshot."""
        current_migrations = set()
        for app_config in settings.INSTALLED_APPS:
            if "." in app_config:
                app_name = app_config.split(".")[-1]
                migrations_dir = Path(settings.BASE_DIR) / "example_project" / app_name / "migrations"
                if migrations_dir.exists():
                    current_migrations.update(str(f.absolute()) for f in migrations_dir.glob("[0-9]*.py"))
        return current_migrations - self.initial_migrations


# Create a single instance to use across tests
migration_tracker = MigrationTracker()


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup database for testing and handle migration cleanup."""
    with django_db_blocker.unblock():
        # Store initial migration state
        initial_db_migrations = {
            (migration.app, migration.name) for migration in MigrationRecorder.Migration.objects.all()
        }

        # Take snapshot of migration files
        migration_tracker.snapshot_migrations()

        yield

        # Clean up migrations created during testing
        with connection.cursor() as cursor:
            # Get current migrations
            final_migrations = {
                (migration.app, migration.name) for migration in MigrationRecorder.Migration.objects.all()
            }

            # Find and remove new migrations from database
            new_migrations = final_migrations - initial_db_migrations
            for app, name in new_migrations:
                cursor.execute("DELETE FROM django_migrations WHERE app = %s AND name = %s", [app, name])

        # Clean up new migration files
        new_migration_files = migration_tracker.get_new_migrations()
        for migration_file in new_migration_files:
            try:
                Path(migration_file).unlink()
            except FileNotFoundError:
                pass  # File was already deleted


@pytest.fixture(autouse=True)
def clean_test_migrations():
    """Track and clean migrations for each test."""
    # Take snapshot before test
    migration_tracker.snapshot_migrations()

    yield

    # Clean up new migration files after test
    new_migration_files = migration_tracker.get_new_migrations()
    for migration_file in new_migration_files:
        try:
            Path(migration_file).unlink()
        except FileNotFoundError:
            pass
