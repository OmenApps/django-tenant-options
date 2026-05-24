"""Command to scaffold a concrete Option and Selection model pair."""

import logging
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_tenant_options import scaffolding
from django_tenant_options.app_settings import TENANT_MODEL


logger = logging.getLogger("django_tenant_options")


NEXT_STEPS_TEMPLATE = """
Next steps:
  1. Edit the generated {name}Option.default_options to define your defaults.
  2. python manage.py makemigrations {app_label}
  3. python manage.py migrate
  4. python manage.py syncoptions
"""


class Command(BaseCommand):
    """Generates a wired-up concrete Option and Selection model pair."""

    help = "Generates a wired-up concrete Option and Selection model pair."

    def add_arguments(self, parser):
        """Define positional and optional arguments."""
        parser.add_argument("app_label", help="The app label to add the models to, for example 'example'.")
        parser.add_argument("name", help="The PascalCase base name for the models, for example 'Priority'.")
        parser.add_argument(
            "--tenant-model",
            dest="tenant_model",
            default=None,
            help="Dotted path to the tenant model. Defaults to the package TENANT_MODEL setting.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the generated code and next steps without writing any files.",
        )
        parser.add_argument(
            "--with-admin",
            action="store_true",
            help="Also generate admin registrations.",
        )
        parser.add_argument(
            "--with-forms",
            action="store_true",
            help="Also generate a SelectionsForm and an OptionCreateForm.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Append even if the class names already appear in the target models.py.",
        )

    def handle(self, *args, **options):
        """Handle the command."""
        app_label = options["app_label"]
        raw_name = options["name"]
        tenant_model = options["tenant_model"] or TENANT_MODEL
        dry_run = options["dry_run"]
        with_admin = options["with_admin"]
        with_forms = options["with_forms"]
        force = options["force"]

        try:
            name = scaffolding.validate_name(raw_name)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        try:
            app_config = apps.get_app_config(app_label)
        except LookupError as exc:
            raise CommandError(f"App label '{app_label}' was not found. Make sure it is in INSTALLED_APPS.") from exc

        app_path = app_config.path
        models_path = os.path.join(app_path, "models.py")

        self._check_for_conflicts(models_path, name, force)

        models_body = scaffolding.render_models_code(name=name, app_label=app_label, tenant_model=tenant_model)
        models_imports = scaffolding.render_models_imports()

        if dry_run:
            self._handle_dry_run(app_label, name, models_imports, models_body, with_admin, with_forms)
            return

        self._handle_write(
            app_path=app_path,
            app_label=app_label,
            name=name,
            models_path=models_path,
            models_imports=models_imports,
            models_body=models_body,
            with_admin=with_admin,
            with_forms=with_forms,
        )

    def _check_for_conflicts(self, models_path, name, force):
        """Raise CommandError if the class names already exist and force is not set."""
        if force or not os.path.exists(models_path):
            return
        with open(models_path, encoding="utf-8") as handle:
            content = handle.read()
        for class_name in (f"class {name}Option", f"class {name}Selection"):
            if class_name in content:
                raise CommandError(
                    f"'{class_name}' already appears in {models_path}. "
                    "Use --force to append anyway or choose a different name."
                )

    def _handle_dry_run(self, app_label, name, models_imports, models_body, with_admin, with_forms):
        """Print generated code and next steps without writing files."""
        self.stdout.write(self.style.NOTICE(f"# {app_label}/models.py"))
        self.stdout.write(models_imports)
        self.stdout.write(models_body)
        if with_admin:
            self.stdout.write(self.style.NOTICE(f"# {app_label}/admin.py"))
            self.stdout.write(scaffolding.render_admin_imports(app_label, name))
            self.stdout.write(scaffolding.render_admin_code(name))
        if with_forms:
            self.stdout.write(self.style.NOTICE(f"# {app_label}/forms.py"))
            self.stdout.write(scaffolding.render_forms_imports(app_label, name))
            self.stdout.write(scaffolding.render_forms_code(name))
        self.stdout.write(NEXT_STEPS_TEMPLATE.format(name=name, app_label=app_label))

    def _handle_write(
        self,
        app_path,
        app_label,
        name,
        models_path,
        models_imports,
        models_body,
        with_admin,
        with_forms,
    ):
        """Append generated code to the app's files and print next steps."""
        scaffolding.append_code_to_file(models_path, models_imports, models_body)
        self.stdout.write(self.style.SUCCESS(f"Wrote {name}Option and {name}Selection to {models_path}"))

        if with_admin:
            admin_path = os.path.join(app_path, "admin.py")
            scaffolding.append_code_to_file(
                admin_path,
                scaffolding.render_admin_imports(app_label, name),
                scaffolding.render_admin_code(name),
            )
            self.stdout.write(self.style.SUCCESS(f"Wrote admin registrations to {admin_path}"))

        if with_forms:
            forms_path = os.path.join(app_path, "forms.py")
            scaffolding.append_code_to_file(
                forms_path,
                scaffolding.render_forms_imports(app_label, name),
                scaffolding.render_forms_code(name),
            )
            self.stdout.write(self.style.SUCCESS(f"Wrote forms to {forms_path}"))

        self.stdout.write(NEXT_STEPS_TEMPLATE.format(name=name, app_label=app_label))
