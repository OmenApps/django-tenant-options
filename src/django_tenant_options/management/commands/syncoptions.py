"""Command to update the project's Options."""

import logging

from django.core.management.base import BaseCommand

from django_tenant_options.choices import OptionType


logger = logging.getLogger("django_tenant_options")


class Command(BaseCommand):
    """Synchronizes the project's Options Lists."""

    help = "Synchronizes the project's Options Lists."

    def syncoptions(self):
        """Synchronize the project's Options Lists."""
        from django_tenant_options.helpers import all_option_subclasses

        model_subclasses = self.get_model_subclasses(all_option_subclasses)
        if not model_subclasses:
            self.stdout.write(self.style.WARNING("No default options found in the project."))  # pylint: disable=E1101
            return

        for ModelClass in model_subclasses:  # pylint: disable=C0103
            updated_options = self.update_options(ModelClass)
            if updated_options:
                self.print_updated_options(ModelClass, updated_options)

    def get_model_subclasses(self, all_option_subclasses):
        """Fetches all model subclasses."""
        try:
            return all_option_subclasses()
        except Exception as e:  # pylint: disable=W0718
            logger.error("Error fetching model subclasses: %s", e)
            return []

    def update_options(self, ModelClass):  # pylint: disable=C0103
        """Updates default options for a given model class."""
        try:
            updated_options = ModelClass.objects._update_default_options()  # pylint: disable=W0212
            return updated_options
        except Exception as e:  # pylint: disable=W0718
            logger.error("Error updating options for %s: %s", ModelClass.__name__, e)
            return {}

    def print_updated_options(self, ModelClass, updated_options):  # pylint: disable=C0103
        """Prints the updated options for a given model class."""
        self.stdout.write(self.style.NOTICE(f"\nModel: {ModelClass.__name__}"))  # pylint: disable=E1101
        self.print_imported_or_verified_options(updated_options)
        self.print_all_active_custom_options(ModelClass)
        self.print_newly_deleted_options(updated_options)
        self.print_all_pre_existing_deleted_options(ModelClass, updated_options)

    def print_imported_or_verified_options(self, updated_options):
        """Prints the imported or verified options."""
        imported_count = sum(1 for options_dict in updated_options.values() if options_dict.get("deleted") is None)
        if imported_count > 0:
            self.stdout.write(self.style.WARNING("  Imported or Verified Options:"))  # pylint: disable=E1101
            for name, options_dict in updated_options.items():
                if options_dict.get("deleted") is None:
                    option_type = dict(OptionType.choices).get(options_dict.get("option_type"))
                    self.stdout.write(f"    - '{name}', Type: {option_type}")
            self.stdout.write(f"    {imported_count} options imported or verified")
        else:
            self.stdout.write(self.style.WARNING("  No options imported or verified"))  # pylint: disable=E1101

    def print_newly_deleted_options(self, updated_options):
        """Prints the newly deleted options."""
        deleted_count = sum(1 for options_dict in updated_options.values() if options_dict.get("deleted") is not None)
        if deleted_count > 0:
            self.stdout.write(self.style.WARNING("  Newly Deleted Options:"))  # pylint: disable=E1101
            for name, options_dict in updated_options.items():
                if options_dict.get("deleted") is not None:
                    self.stdout.write(f"    - '{name}'")
            self.stdout.write(f"    {deleted_count} Newly Deleted Options")
        else:
            self.stdout.write(self.style.WARNING("  No Newly Deleted Options"))  # pylint: disable=E1101

    def print_all_pre_existing_deleted_options(self, ModelClass, updated_options):  # pylint: disable=C0103
        """Prints all pre-existing deleted options not in the updated options."""
        all_pre_existing_deleted = ModelClass.objects.deleted().exclude(name__in=updated_options.keys())
        if all_pre_existing_deleted.exists():
            self.stdout.write(self.style.WARNING("  All Pre-existing Deleted Options:"))  # pylint: disable=E1101
            for option in all_pre_existing_deleted:
                self.stdout.write(f"    - '{option.name}', Type: {option.get_option_type_display()}")
            self.stdout.write(f"    {all_pre_existing_deleted.count()} Pre-existing Deleted Options")
        else:
            self.stdout.write(self.style.WARNING("  No Pre-existing Deleted Options"))  # pylint: disable=E1101

    def print_all_active_custom_options(self, ModelClass):  # pylint: disable=C0103
        """Prints all custom options."""
        custom_options = ModelClass.objects.custom_options().active()
        if custom_options.exists():
            self.stdout.write(self.style.WARNING("  All Custom Options:"))  # pylint: disable=E1101
            for option in custom_options:
                self.stdout.write(f"    - '{option.name}', Tenant: {option.tenant}")
            self.stdout.write(f"    {custom_options.count()} Custom Options")
        else:
            self.stdout.write(self.style.WARNING("  No Custom Options"))  # pylint: disable=E1101

    def handle(self, *args, **kwargs):  # pylint: disable=W0613
        """Handle the command."""
        self.syncoptions()
