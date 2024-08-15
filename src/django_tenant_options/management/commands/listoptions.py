"""Command to list all of the project's Options."""

import logging

from django.core.management.base import BaseCommand


logger = logging.getLogger("django_tenant_options")


class Command(BaseCommand):
    """Lists all of the project's Options that are active (not soft-deleted)."""

    help = "Lists all of the project's Options that are active (not soft-deleted)."

    def listoptions(self):
        """List all of the project's Options that are active (not soft-deleted)."""
        from django_tenant_options.helpers import all_option_subclasses

        try:
            model_subclasses = all_option_subclasses()

            if not model_subclasses:
                print("No options found in the project.")
                return

            for ModelClass in all_option_subclasses():  # pylint: disable=C0103
                self.stdout.write(self.style.NOTICE(f"Model: {ModelClass.__name__}"))
                self.stdout.write(self.style.WARNING("  Options:"))
                for option in ModelClass.objects.active():
                    if option.tenant is not None:
                        print(f"    - {option.name} (Tenant: {option.tenant})")
                    else:
                        print(f"    - {option.name}")
                print()
        except Exception as e:  # pylint: disable=W0703
            logger.error("Error: %s", e)

    def handle(self, *args, **kwargs):  # pylint: disable=W0613
        """Handle the command."""
        self.listoptions()
