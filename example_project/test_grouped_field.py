"""Test cases for the grouped option multiple-choice field."""

import pytest
from django.utils.module_loading import import_string as import_from_string

from django_tenant_options.choices import OptionType
from django_tenant_options.form_fields import GroupedModelChoiceIterator
from django_tenant_options.form_fields import GroupedOptionsModelMultipleChoiceField
from django_tenant_options.form_fields import OptionsModelMultipleChoiceField
from django_tenant_options.forms import SelectionsForm
from example_project.example.models import TaskPriorityOption
from example_project.example.models import TaskPrioritySelection
from example_project.example.models import Tenant


def test_imports_available():
    """The grouped field, iterator, base field, and OptionType import cleanly."""
    assert issubclass(GroupedOptionsModelMultipleChoiceField, OptionsModelMultipleChoiceField)
    assert GroupedModelChoiceIterator is not None
    assert OptionType.MANDATORY == "dm"
    assert SelectionsForm is not None
    assert TaskPriorityOption is not None
    assert TaskPrioritySelection is not None
    assert Tenant is not None


@pytest.mark.django_db
class TestGroupByOptionType:
    """Grouping by option_type produces ordered ``<optgroup>`` tuples."""

    def _build_field(self, tenant):
        """Create options of every type and return a field over them."""
        TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Low", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Medium", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Spicy", option_type=OptionType.CUSTOM, tenant=tenant)
        queryset = TaskPriorityOption.objects.all().order_by("name")
        return GroupedOptionsModelMultipleChoiceField(queryset=queryset)

    def test_top_level_items_are_group_tuples(self):
        """Each top-level choice is a ``(group_label, [choices])`` tuple."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        field = self._build_field(tenant)

        choices = list(field.choices)

        for item in choices:
            assert isinstance(item, tuple)
            group_label, group_choices = item
            assert isinstance(group_label, str)
            assert isinstance(group_choices, list)

    def test_group_order_and_labels(self):
        """Groups appear in Mandatory -> Optional -> Custom order with OptionType display labels."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        field = self._build_field(tenant)

        group_labels = [group_label for group_label, _ in field.choices]

        assert group_labels == ["Default Mandatory", "Default Optional", "Custom"]

    def test_each_group_contains_correct_options(self):
        """Options land in the group matching their option_type."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        field = self._build_field(tenant)

        grouped = {group_label: [label for _, label in entries] for group_label, entries in field.choices}

        assert sorted(grouped["Default Mandatory"]) == ["High (mandatory)", "Low (mandatory)"]
        assert sorted(grouped["Default Optional"]) == ["Critical (optional)", "Medium (optional)"]
        assert grouped["Custom"] == ["Spicy (custom)"]

    def test_empty_group_is_omitted(self):
        """A group with no members is not yielded."""
        Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        queryset = TaskPriorityOption.objects.all().order_by("name")
        field = GroupedOptionsModelMultipleChoiceField(queryset=queryset)

        group_labels = [group_label for group_label, _ in field.choices]

        assert group_labels == ["Default Mandatory", "Default Optional"]
        assert "Custom" not in group_labels


@pytest.mark.django_db
class TestGroupedLabels:
    """The inherited label_from_instance still appends the type suffix inside groups."""

    def test_labels_include_type_suffix(self):
        """Labels inside groups read like 'Name (mandatory)' / '(optional)' / '(custom)'."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Spicy", option_type=OptionType.CUSTOM, tenant=tenant)
        queryset = TaskPriorityOption.objects.all().order_by("name")
        field = GroupedOptionsModelMultipleChoiceField(queryset=queryset)

        all_labels = [label for _, entries in field.choices for _, label in entries]

        assert "High (mandatory)" in all_labels
        assert "Critical (optional)" in all_labels
        assert "Spicy (custom)" in all_labels

    def test_label_from_instance_matches_base_field(self):
        """label_from_instance behaves identically to the non-grouped base field."""
        Tenant.objects.create(name="T", subdomain="t")
        option = TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        grouped = GroupedOptionsModelMultipleChoiceField(queryset=TaskPriorityOption.objects.all())
        base = OptionsModelMultipleChoiceField(queryset=TaskPriorityOption.objects.all())

        assert grouped.label_from_instance(option) == base.label_from_instance(option)
        assert grouped.label_from_instance(option) == "High (mandatory)"


@pytest.mark.django_db
class TestGroupByAttribute:
    """Grouping by an arbitrary attribute degrades gracefully when the attribute is missing."""

    def test_missing_attribute_all_uncategorized(self):
        """When the model lacks the group_by attribute, all options bucket into 'Uncategorized'."""
        Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        queryset = TaskPriorityOption.objects.all().order_by("name")
        field = GroupedOptionsModelMultipleChoiceField(queryset=queryset, group_by="category")

        group_labels = [group_label for group_label, _ in field.choices]

        assert group_labels == ["Uncategorized"]
        members = [label for _, entries in field.choices for _, label in entries]
        assert "High (mandatory)" in members
        assert "Critical (optional)" in members

    def test_attribute_present_splits_groups(self):
        """When objects carry the group_by attribute, they split into alphabetically-ordered groups.

        The example model has no 'category' column, so we drive the iterator directly with a
        stub field whose queryset is the in-memory instances (which carry an in-memory category)
        and which reuses the real field's label_from_instance.
        """
        Tenant.objects.create(name="T", subdomain="t")
        a1 = TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        a2 = TaskPriorityOption.objects.create(name="Low", option_type=OptionType.MANDATORY)
        b1 = TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        none1 = TaskPriorityOption.objects.create(name="Medium", option_type=OptionType.OPTIONAL)

        a1.category = "A"
        a2.category = "A"
        b1.category = "B"
        none1.category = ""

        real_field = GroupedOptionsModelMultipleChoiceField(
            queryset=TaskPriorityOption.objects.all(), group_by="category"
        )

        class _StubField:
            """Minimal field stand-in exposing only what GroupedModelChoiceIterator reads."""

            empty_label = None
            group_by = "category"
            queryset = [a1, a2, b1, none1]

            def prepare_value(self, obj):
                return obj.pk

            def label_from_instance(self, obj):
                return real_field.label_from_instance(obj)

        groups = list(GroupedModelChoiceIterator(_StubField()))

        group_labels = [group_label for group_label, _ in groups]
        assert group_labels == ["A", "B", "Uncategorized"]
        grouped = {gl: [label for _, label in entries] for gl, entries in groups}
        assert sorted(grouped["A"]) == ["High (mandatory)", "Low (mandatory)"]
        assert grouped["B"] == ["Critical (optional)"]
        assert grouped["Uncategorized"] == ["Medium (optional)"]


@pytest.mark.django_db
class TestGroupedRendering:
    """The widget renders ``<optgroup>`` elements for grouped choices."""

    def test_widget_renders_optgroup(self):
        """Rendering the widget with the grouped choices emits <optgroup ...>."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Spicy", option_type=OptionType.CUSTOM, tenant=tenant)
        queryset = TaskPriorityOption.objects.all().order_by("name")
        field = GroupedOptionsModelMultipleChoiceField(queryset=queryset)

        html = str(field.widget.render("selections", [], {"choices": list(field.choices)}))

        assert "<optgroup" in html
        assert 'label="Default Mandatory"' in html
        assert 'label="Default Optional"' in html
        assert 'label="Custom"' in html
        assert "High (mandatory)" in html


@pytest.mark.django_db
class TestPerFormOptIn:
    """A SelectionsForm subclass can opt into the grouped field via a class attribute."""

    class GroupedSelectionsForm(SelectionsForm):
        """SelectionsForm subclass that uses the grouped field."""

        __test__ = False

        multiple_choice_field_class = GroupedOptionsModelMultipleChoiceField

        class Meta:
            """Meta class for the form."""

            model = TaskPrioritySelection

    class PlainSelectionsForm(SelectionsForm):
        """SelectionsForm subclass with no override (uses the package default)."""

        __test__ = False

        class Meta:
            """Meta class for the form."""

            model = TaskPrioritySelection

    def test_subclass_uses_grouped_field(self):
        """The selections field is the grouped field when the attribute is set."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        form = self.GroupedSelectionsForm(tenant=tenant)

        assert isinstance(form.fields["selections"], GroupedOptionsModelMultipleChoiceField)

    def test_default_form_unchanged(self):
        """A subclass without the attribute keeps the default (non-grouped) field type."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        form = self.PlainSelectionsForm(tenant=tenant)

        assert isinstance(form.fields["selections"], OptionsModelMultipleChoiceField)
        assert not isinstance(form.fields["selections"], GroupedOptionsModelMultipleChoiceField)

    def test_grouped_form_choices_have_groups(self):
        """The grouped form's selections field yields optgroup tuples."""
        tenant = Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="High", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Critical", option_type=OptionType.OPTIONAL)
        form = self.GroupedSelectionsForm(tenant=tenant)

        choices = list(form.fields["selections"].choices)

        assert all(isinstance(group_choices, list) for _, group_choices in choices)
        group_labels = [group_label for group_label, _ in choices]
        assert "Default Mandatory" in group_labels


@pytest.mark.django_db
class TestProjectWideOverride:
    """The grouped field is usable as the project-wide DEFAULT_MULTIPLE_CHOICE_FIELD."""

    DOTTED_PATH = "django_tenant_options.form_fields.GroupedOptionsModelMultipleChoiceField"

    def test_dotted_path_resolves_to_grouped_field(self):
        """The documented dotted path imports the grouped field class."""
        resolved = import_from_string(self.DOTTED_PATH)
        assert resolved is GroupedOptionsModelMultipleChoiceField

    def test_form_uses_patched_default(self, monkeypatch):
        """When the form's default field symbol is the grouped field, plain forms use it."""
        import django_tenant_options.forms as forms_module

        monkeypatch.setattr(forms_module, "DEFAULT_MULTIPLE_CHOICE_FIELD", GroupedOptionsModelMultipleChoiceField)

        class PlainForm(SelectionsForm):
            __test__ = False

            class Meta:
                model = TaskPrioritySelection

        tenant = Tenant.objects.create(name="T", subdomain="t")
        form = PlainForm(tenant=tenant)

        assert isinstance(form.fields["selections"], GroupedOptionsModelMultipleChoiceField)
