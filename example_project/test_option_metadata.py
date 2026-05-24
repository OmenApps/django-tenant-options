"""Test cases for the OptionMetadataMixin and the example TagOption/TagSelection models."""

import pytest

from django_tenant_options.choices import OptionType
from django_tenant_options.mixins import OptionMetadataMixin
from example_project.example.models import TagOption


def test_mixin_is_abstract():
    """The mixin must be an abstract Django model so it can be mixed into concrete Options."""
    assert OptionMetadataMixin._meta.abstract is True


def test_mixin_declares_expected_fields():
    """The mixin must declare exactly the four metadata fields with the expected names."""
    field_names = {field.name for field in OptionMetadataMixin._meta.get_fields()}
    assert {"description", "help_text", "sort_order", "category"}.issubset(field_names)


def test_mixin_field_configuration():
    """The mixin fields must have the documented types, lengths, indexes, and defaults."""
    fields = {field.name: field for field in OptionMetadataMixin._meta.get_fields()}

    description = fields["description"]
    assert description.get_internal_type() == "TextField"
    assert description.blank is True
    assert description.default == ""

    help_text = fields["help_text"]
    assert help_text.get_internal_type() == "CharField"
    assert help_text.max_length == 255
    assert help_text.blank is True
    assert help_text.default == ""

    sort_order = fields["sort_order"]
    assert sort_order.get_internal_type() == "IntegerField"
    assert sort_order.default == 0
    assert sort_order.db_index is True

    category = fields["category"]
    assert category.get_internal_type() == "CharField"
    assert category.max_length == 100
    assert category.blank is True
    assert category.default == ""


@pytest.mark.django_db
class TestTagOptionMetadata:
    """Tests exercising OptionMetadataMixin through the concrete TagOption model."""

    def test_metadata_defaults_when_only_name_given(self):
        """Creating a TagOption with only a name must yield empty/zero metadata defaults."""
        option = TagOption.objects.create(name="Solo", option_type=OptionType.OPTIONAL)
        assert option.description == ""
        assert option.help_text == ""
        assert option.sort_order == 0
        assert option.category == ""

    def test_metadata_values_persist(self):
        """Explicit metadata values must round-trip through the database."""
        TagOption.objects.create(
            name="Documented",
            option_type=OptionType.OPTIONAL,
            description="A longer description.",
            help_text="Shown next to the field.",
            sort_order=5,
            category="colors",
        )
        option = TagOption.objects.get(name="Documented")
        assert option.description == "A longer description."
        assert option.help_text == "Shown next to the field."
        assert option.sort_order == 5
        assert option.category == "colors"

    def test_default_ordering_by_sort_order_then_name(self):
        """The default queryset must order by sort_order, then by name."""
        TagOption.objects.create(name="Gamma", option_type=OptionType.OPTIONAL, sort_order=30)
        TagOption.objects.create(name="Alpha", option_type=OptionType.OPTIONAL, sort_order=10)
        TagOption.objects.create(name="Beta", option_type=OptionType.OPTIONAL, sort_order=20)

        ordered_names = list(TagOption.objects.active().values_list("name", flat=True))

        assert ordered_names == ["Alpha", "Beta", "Gamma"]

    def test_ordering_tiebreak_on_name(self):
        """When sort_order ties, the queryset must fall back to name ordering."""
        TagOption.objects.create(name="Zeta", option_type=OptionType.OPTIONAL, sort_order=0)
        TagOption.objects.create(name="Apple", option_type=OptionType.OPTIONAL, sort_order=0)

        ordered_names = list(TagOption.objects.active().values_list("name", flat=True))

        assert ordered_names == ["Apple", "Zeta"]

    def test_filter_by_category(self):
        """Filtering by category must return only options in that category."""
        TagOption.objects.create(name="Red", option_type=OptionType.OPTIONAL, category="A")
        TagOption.objects.create(name="Green", option_type=OptionType.OPTIONAL, category="A")
        TagOption.objects.create(name="Blue", option_type=OptionType.OPTIONAL, category="B")

        category_a = set(TagOption.objects.filter(category="A").values_list("name", flat=True))
        category_b = set(TagOption.objects.filter(category="B").values_list("name", flat=True))

        assert category_a == {"Red", "Green"}
        assert category_b == {"Blue"}

    def test_mixin_composes_with_soft_delete(self):
        """A TagOption (mixin + AbstractOption) must support soft delete via .deleted()."""
        option = TagOption.objects.create(name="Temporary", option_type=OptionType.OPTIONAL, category="A")

        option.delete()

        assert option.pk is not None
        assert TagOption.objects.active().filter(pk=option.pk).count() == 0
        assert TagOption.objects.deleted().filter(pk=option.pk).count() == 1

    def test_soft_deleted_option_retains_metadata(self):
        """Soft deletion must not clear the metadata fields."""
        option = TagOption.objects.create(
            name="Archived",
            option_type=OptionType.OPTIONAL,
            description="kept",
            sort_order=7,
            category="A",
        )

        option.delete()

        reloaded = TagOption.objects.deleted().get(pk=option.pk)
        assert reloaded.description == "kept"
        assert reloaded.sort_order == 7
        assert reloaded.category == "A"
