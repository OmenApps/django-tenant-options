"""Tests for the scaffolding module and the startoptions management command."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from django_tenant_options import scaffolding


class TestValidateName:
    """Unit tests for scaffolding.validate_name (no database needed)."""

    def test_accepts_pascal_case(self):
        """A valid PascalCase identifier is returned unchanged."""
        assert scaffolding.validate_name("Priority") == "Priority"

    def test_accepts_multi_word_pascal_case(self):
        """A multi-word PascalCase identifier is returned unchanged."""
        assert scaffolding.validate_name("TaskPriority") == "TaskPriority"

    def test_rejects_empty_string(self):
        """An empty name raises ValueError."""
        with pytest.raises(ValueError):
            scaffolding.validate_name("")

    def test_rejects_non_identifier(self):
        """A name that is not a valid Python identifier raises ValueError."""
        with pytest.raises(ValueError):
            scaffolding.validate_name("Priority-1")

    def test_rejects_leading_digit(self):
        """A name starting with a digit raises ValueError."""
        with pytest.raises(ValueError):
            scaffolding.validate_name("1Priority")

    def test_rejects_lowercase_first_letter(self):
        """A name not starting with an uppercase letter raises ValueError."""
        with pytest.raises(ValueError):
            scaffolding.validate_name("priority")


class TestRenderModelsCode:
    """Unit tests for scaffolding.render_models_code (no database needed)."""

    def _render(self):
        """Render models code for a typical Priority pair in the example app."""
        return scaffolding.render_models_code(
            name="Priority",
            app_label="example",
            tenant_model="example.Tenant",
        )

    def test_imports_helper_includes_import_lines(self):
        """render_models_imports provides the abstract bases and OptionType imports."""
        code = scaffolding.render_models_imports()
        assert "from django_tenant_options.models import AbstractOption" in code
        assert "from django_tenant_options.models import AbstractSelection" in code
        assert "from django_tenant_options.choices import OptionType" in code

    def test_body_excludes_import_lines(self):
        """render_models_code returns body only; imports are supplied separately."""
        code = self._render()
        assert "import" not in code

    def test_defines_option_class(self):
        """The rendered code defines the Option subclass."""
        code = self._render()
        assert "class PriorityOption(AbstractOption):" in code

    def test_defines_selection_class(self):
        """The rendered code defines the Selection subclass."""
        code = self._render()
        assert "class PrioritySelection(AbstractSelection):" in code

    def test_option_wires_selection_model(self):
        """The Option points at the Selection via selection_model."""
        code = self._render()
        assert 'selection_model = "example.PrioritySelection"' in code

    def test_option_has_default_options_placeholder(self):
        """The Option includes an empty default_options placeholder with a hint."""
        code = self._render()
        assert "default_options = {}" in code
        assert "OptionType.MANDATORY" in code

    def test_selection_wires_tenant_and_option_models(self):
        """The Selection points at the tenant and the Option."""
        code = self._render()
        assert 'tenant_model = "example.Tenant"' in code
        assert 'option_model = "example.PriorityOption"' in code

    def test_meta_inheritance(self):
        """Both Meta classes inherit from the abstract Meta classes."""
        code = self._render()
        assert "class Meta(AbstractOption.Meta):" in code
        assert "class Meta(AbstractSelection.Meta):" in code


class TestRenderAdminCode:
    """Unit tests for scaffolding.render_admin_code (no database needed)."""

    def test_imports_base_admin_classes(self):
        """render_admin_imports provides the package base admin classes."""
        code = scaffolding.render_admin_imports("example_project.example", "Priority")
        assert "from django_tenant_options.admin import BaseOptionsAdmin" in code
        assert "from django_tenant_options.admin import BaseSelectionsAdmin" in code
        assert "from example_project.example.models import PriorityOption" in code

    def test_registers_option_and_selection(self):
        """The rendered admin registers both generated models."""
        code = scaffolding.render_admin_code("Priority")
        assert "@admin.register(PriorityOption)" in code
        assert "@admin.register(PrioritySelection)" in code
        assert "class PriorityOptionAdmin(BaseOptionsAdmin):" in code
        assert "class PrioritySelectionAdmin(BaseSelectionsAdmin):" in code


class TestRenderFormsCode:
    """Unit tests for scaffolding.render_forms_code (no database needed)."""

    def test_imports_form_helpers(self):
        """render_forms_imports provides the package form helpers and django forms."""
        code = scaffolding.render_forms_imports("example_project.example", "Priority")
        assert "from django import forms" in code
        assert "from django_tenant_options.forms import OptionCreateFormMixin" in code
        assert "from django_tenant_options.forms import SelectionsForm" in code
        assert "from example_project.example.models import PriorityOption" in code

    def test_defines_selections_form(self):
        """The rendered forms define a SelectionsForm subclass with a Meta model."""
        code = scaffolding.render_forms_code("Priority")
        assert "class PrioritySelectionsForm(SelectionsForm):" in code
        assert "model = PrioritySelection" in code

    def test_defines_option_create_form(self):
        """The rendered forms define an OptionCreateForm using the mixin."""
        code = scaffolding.render_forms_code("Priority")
        assert "class PriorityOptionCreateForm(OptionCreateFormMixin, forms.ModelForm):" in code
        assert "model = PriorityOption" in code
        # The create form must expose only the name field; the mixin manages
        # option_type, tenant, and deleted so they must not be in fields.
        assert 'fields = ["name"]' in code
        assert 'fields = "__all__"' not in code


class TestAppendCodeToFile:
    """Unit tests for scaffolding.append_code_to_file using tmp_path only."""

    def test_creates_file_when_missing(self, tmp_path):
        """Appending to a non-existent file creates it with header and body."""
        target = tmp_path / "models.py"
        scaffolding.append_code_to_file(
            str(target),
            imports="from django.db import models\n",
            body="class Foo:\n    pass\n",
        )
        text = target.read_text()
        assert "from django.db import models" in text
        assert "class Foo:" in text

    def test_appends_body_to_existing_file(self, tmp_path):
        """Appending to an existing file keeps prior content and adds the body."""
        target = tmp_path / "models.py"
        target.write_text("# existing header\nEXISTING = True\n")
        scaffolding.append_code_to_file(
            str(target),
            imports="from django.db import models\n",
            body="class Bar:\n    pass\n",
        )
        text = target.read_text()
        assert "EXISTING = True" in text
        assert "class Bar:" in text

    def test_does_not_duplicate_existing_import(self, tmp_path):
        """An import line already present in the file is not added twice."""
        target = tmp_path / "models.py"
        target.write_text("from django.db import models\nEXISTING = True\n")
        scaffolding.append_code_to_file(
            str(target),
            imports="from django.db import models\n",
            body="class Baz:\n    pass\n",
        )
        text = target.read_text()
        assert text.count("from django.db import models") == 1
        assert "class Baz:" in text

    def test_dedup_is_line_based_not_substring(self, tmp_path):
        """A distinct import that is a substring of an existing one is still added."""
        target = tmp_path / "models.py"
        target.write_text("from example.models import PriorityOption\n")
        scaffolding.append_code_to_file(
            str(target),
            imports="from example.models import Priority\n",
            body="class Qux:\n    pass\n",
        )
        text = target.read_text()
        assert "from example.models import Priority\n" in text
        assert "from example.models import PriorityOption" in text

    def test_handles_existing_file_without_trailing_newline(self, tmp_path):
        """Appending to a file with no trailing newline does not join lines together."""
        target = tmp_path / "models.py"
        target.write_text("FOO = 1")
        scaffolding.append_code_to_file(
            str(target),
            imports="import os\n",
            body="class Quux:\n    pass\n",
        )
        text = target.read_text()
        assert "FOO = 1import" not in text
        assert "FOO = 1\n" in text
        assert "import os" in text


@pytest.mark.django_db
class TestStartOptionsCommandValidation:
    """Validation behaviour of the startoptions management command."""

    def test_unknown_app_label_raises_command_error(self):
        """An app_label that does not exist raises CommandError."""
        out = StringIO()
        with pytest.raises(CommandError):
            call_command("startoptions", "nonexistent_app", "Priority", "--dry-run", stdout=out)

    def test_invalid_name_raises_command_error(self):
        """A name that is not valid PascalCase raises CommandError."""
        out = StringIO()
        with pytest.raises(CommandError):
            call_command("startoptions", "example", "priority", "--dry-run", stdout=out)


@pytest.mark.django_db
class TestStartOptionsDryRun:
    """Dry-run behaviour of the startoptions management command."""

    def _example_models_path(self):
        """Return the absolute path to the example app's models.py."""
        import os

        from django.apps import apps

        return os.path.join(apps.get_app_config("example").path, "models.py")

    def test_dry_run_prints_model_classes(self):
        """Dry-run output contains the generated class definitions."""
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "class PriorityOption(AbstractOption):" in output
        assert "class PrioritySelection(AbstractSelection):" in output
        assert 'selection_model = "example.PrioritySelection"' in output

    def test_dry_run_prints_next_steps(self):
        """Dry-run output contains the next-steps guidance."""
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "Next steps:" in output
        assert "makemigrations example" in output
        assert "syncoptions" in output

    def test_dry_run_does_not_modify_models_file(self):
        """Dry-run must not touch the example app's models.py."""
        import os

        path = self._example_models_path()
        before = os.path.getmtime(path)
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--dry-run", stdout=out)
        after = os.path.getmtime(path)
        assert before == after
        assert "class PriorityOption(AbstractOption):" not in open(path, encoding="utf-8").read()

    def test_dry_run_with_admin_includes_admin_snippet(self):
        """Dry-run with --with-admin prints admin registrations."""
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--dry-run", "--with-admin", stdout=out)
        output = out.getvalue()
        assert "@admin.register(PriorityOption)" in output
        assert "class PriorityOptionAdmin(BaseOptionsAdmin):" in output
        assert "@admin.register(PrioritySelection)" in output
        # Import must use the full importable module path, not just the app label.
        assert "from example_project.example.models import PriorityOption" in output
        assert "from example.models import" not in output

    def test_dry_run_with_forms_includes_forms_snippet(self):
        """Dry-run with --with-forms prints the forms."""
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--dry-run", "--with-forms", stdout=out)
        output = out.getvalue()
        assert "class PrioritySelectionsForm(SelectionsForm):" in output
        assert "class PriorityOptionCreateForm(OptionCreateFormMixin, forms.ModelForm):" in output
        # Import must use the full importable module path, not just the app label.
        assert "from example_project.example.models import PriorityOption" in output
        assert "from example.models import" not in output

    def test_dry_run_without_flags_omits_admin_and_forms(self):
        """Dry-run without the optional flags omits admin and forms snippets."""
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "@admin.register" not in output
        assert "SelectionsForm" not in output


@pytest.mark.django_db
class TestStartOptionsWrite:
    """Real file-write behaviour of startoptions, isolated to tmp_path."""

    def _patch_app_path(self, monkeypatch, tmp_path):
        """Point the example app config path at tmp_path for the test."""
        from django.apps import apps

        app_config = apps.get_app_config("example")
        monkeypatch.setattr(app_config, "path", str(tmp_path))

    def test_write_creates_models_in_tmp_dir(self, monkeypatch, tmp_path):
        """A non-dry-run write appends the models to tmp_path/models.py."""
        import os

        self._patch_app_path(monkeypatch, tmp_path)
        out = StringIO()
        call_command("startoptions", "example", "Priority", stdout=out)

        models_file = tmp_path / "models.py"
        assert models_file.exists()
        text = models_file.read_text()
        assert "class PriorityOption(AbstractOption):" in text
        assert "class PrioritySelection(AbstractSelection):" in text
        assert "Next steps:" in out.getvalue()
        # admin.py and forms.py were not requested, so they must not exist.
        assert not os.path.exists(tmp_path / "admin.py")
        assert not os.path.exists(tmp_path / "forms.py")

    def test_write_with_admin_and_forms_creates_all_files(self, monkeypatch, tmp_path):
        """A non-dry-run write with both flags creates models, admin, and forms."""
        self._patch_app_path(monkeypatch, tmp_path)
        out = StringIO()
        call_command("startoptions", "example", "Priority", "--with-admin", "--with-forms", stdout=out)

        assert (tmp_path / "models.py").exists()
        assert "@admin.register(PriorityOption)" in (tmp_path / "admin.py").read_text()
        assert "class PrioritySelectionsForm(SelectionsForm):" in (tmp_path / "forms.py").read_text()

    def test_write_respects_custom_tenant_model(self, monkeypatch, tmp_path):
        """The --tenant-model option is reflected in the generated source."""
        self._patch_app_path(monkeypatch, tmp_path)
        out = StringIO()
        call_command(
            "startoptions",
            "example",
            "Priority",
            "--tenant-model",
            "other.CustomTenant",
            stdout=out,
        )
        text = (tmp_path / "models.py").read_text()
        assert 'tenant_model = "other.CustomTenant"' in text

    def test_conflict_without_force_raises(self, monkeypatch, tmp_path):
        """Re-running without --force when the class already exists raises CommandError."""
        self._patch_app_path(monkeypatch, tmp_path)
        call_command("startoptions", "example", "Priority", stdout=StringIO())
        with pytest.raises(CommandError):
            call_command("startoptions", "example", "Priority", stdout=StringIO())

    def test_conflict_with_force_appends(self, monkeypatch, tmp_path):
        """Re-running with --force when the class already exists appends a second copy."""
        self._patch_app_path(monkeypatch, tmp_path)
        call_command("startoptions", "example", "Priority", stdout=StringIO())
        call_command("startoptions", "example", "Priority", "--force", stdout=StringIO())
        text = (tmp_path / "models.py").read_text()
        assert text.count("class PriorityOption(AbstractOption):") == 2


class TestGeneratedCodeIsValidPython:
    """Ensure rendered source strings compile without syntax errors."""

    def test_models_code_compiles(self):
        """Rendered models source (imports + body) compiles."""
        code = (
            scaffolding.render_models_imports()
            + "\n\n"
            + scaffolding.render_models_code(
                name="Priority",
                app_label="example",
                tenant_model="example.Tenant",
            )
        )
        compile(code, "<generated-models>", "exec")

    def test_admin_code_compiles(self):
        """Rendered admin source (imports + body) compiles."""
        code = (
            scaffolding.render_admin_imports("example_project.example", "Priority")
            + "\n\n"
            + scaffolding.render_admin_code("Priority")
        )
        compile(code, "<generated-admin>", "exec")

    def test_forms_code_compiles(self):
        """Rendered forms source (imports + body) compiles."""
        code = (
            scaffolding.render_forms_imports("example_project.example", "Priority")
            + "\n\n"
            + scaffolding.render_forms_code("Priority")
        )
        compile(code, "<generated-forms>", "exec")


class TestRenderFormsAccessibility:
    """Generated forms must include descriptive labels and help_text."""

    def _render(self):
        return scaffolding.render_forms_code(name="Priority")

    def test_selections_form_sets_label_and_help_text(self):
        code = self._render()
        assert 'self.fields["selections"].label' in code
        assert 'self.fields["selections"].help_text' in code

    def test_create_form_sets_labels_and_help_texts(self):
        code = self._render()
        assert "labels = {" in code
        assert "help_texts = {" in code

    def test_generated_forms_have_a_review_todo(self):
        code = self._render()
        assert "TODO" in code

    # Python validity of the generated forms code is covered by
    # TestGeneratedCodeIsValidPython.test_forms_code_compiles.
