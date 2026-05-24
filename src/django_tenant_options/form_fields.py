"""Custom form fields for the django_tenant_options app."""

from django import forms
from django.forms.models import ModelChoiceIterator
from django.utils.translation import gettext_lazy as _

from django_tenant_options.choices import OptionType


class OptionsModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Displays objects and shows which are mandatory."""

    def label_from_instance(self, obj) -> str:
        """Return a label for each object."""
        labels = {
            OptionType.MANDATORY: f"{obj.name} (mandatory)",
            OptionType.OPTIONAL: f"{obj.name} (optional)",
            OptionType.CUSTOM: f"{obj.name} (custom)",
        }

        return labels.get(obj.option_type) or str(obj.name)


class GroupedModelChoiceIterator(ModelChoiceIterator):
    """Yields choices grouped into ``<optgroup>`` tuples.

    The grouping key is read from the field's ``group_by`` attribute (a string,
    default ``"option_type"``).

    - When ``group_by == "option_type"``, each group's value is mapped to its human
      label via ``dict(OptionType.choices)`` and groups are ordered Mandatory ->
      Optional -> Custom.
    - For any other attribute, objects are grouped by ``getattr(obj, group_by, "")``.
      An empty/missing value is bucketed under the label ``"Uncategorized"`` and the
      remaining group labels are sorted alphabetically.

    Within each group, the queryset's own ordering is preserved.
    """

    def __iter__(self):
        """Yield an optional empty label, then ``(group_label, [choices])`` tuples."""
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)

        group_by = getattr(self.field, "group_by", "option_type")

        # Materialize the queryset once so we can both group and preserve order.
        objects = list(self.queryset)

        if group_by == "option_type":
            yield from self._iter_by_option_type(objects)
        else:
            yield from self._iter_by_attribute(objects, group_by)

    def _iter_by_option_type(self, objects):
        """Group objects by their ``option_type`` in Mandatory -> Optional -> Custom order."""
        labels = dict(OptionType.choices)
        ordered_types = [OptionType.MANDATORY, OptionType.OPTIONAL, OptionType.CUSTOM]

        buckets = {option_type: [] for option_type in ordered_types}
        for obj in objects:
            buckets.setdefault(obj.option_type, []).append(obj)

        for option_type in ordered_types:
            group_objects = buckets.get(option_type, [])
            if not group_objects:
                continue
            group_label = str(labels.get(option_type, option_type))
            yield (group_label, [self.choice(obj) for obj in group_objects])

    def _iter_by_attribute(self, objects, group_by):
        """Group objects by an arbitrary attribute, bucketing empties under ``Uncategorized``."""
        uncategorized_label = str(_("Uncategorized"))
        buckets = {}
        for obj in objects:
            value = getattr(obj, group_by, "")
            key = str(value) if value not in (None, "") else uncategorized_label
            buckets.setdefault(key, []).append(obj)

        # Alphabetical group order, with "Uncategorized" sorted in naturally by name.
        for group_label in sorted(buckets.keys()):
            group_objects = buckets[group_label]
            yield (group_label, [self.choice(obj) for obj in group_objects])


class GroupedOptionsModelMultipleChoiceField(OptionsModelMultipleChoiceField):
    """A multiple-choice field that renders selectable options inside ``<optgroup>`` groups.

    Drop-in replacement for :class:`OptionsModelMultipleChoiceField`. Set ``group_by`` to
    choose the grouping key (default ``"option_type"``). The inherited
    ``label_from_instance`` is preserved, so option labels still show the type suffix
    (for example ``"High (mandatory)"``) inside each group.
    """

    iterator = GroupedModelChoiceIterator

    def __init__(self, *args, group_by="option_type", **kwargs):
        """Store the grouping key before delegating to the parent field."""
        self.group_by = group_by
        super().__init__(*args, **kwargs)
