"""Optional reusable mixins for django-tenant-options concrete models.

These mixins are opt-in. They subclass ``django.db.models.Model`` (abstract)
rather than the package's configurable base model so that they compose with
``AbstractOption`` regardless of the project's ``MODEL_CLASS`` setting.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class OptionMetadataMixin(models.Model):
    """Add rich, self-documenting metadata fields to a concrete Option model.

    Combine this mixin with ``AbstractOption`` using multiple inheritance, listing
    the mixin first so its fields and ``Meta`` resolve predictably::

        class MyOption(OptionMetadataMixin, AbstractOption):
            tenant_model = "myapp.Tenant"
            selection_model = "myapp.MySelection"

            class Meta(AbstractOption.Meta):
                ordering = ("sort_order", "name")

    Setting ``ordering = ("sort_order", "name")`` in the concrete model's ``Meta``
    is recommended so options are returned in a stable, human-curated order.

    Categories are free-form strings. Filter by category with the standard ORM,
    for example ``MyOption.objects.filter(category="colors")``.
    """

    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
    )
    help_text = models.CharField(
        _("Help Text"),
        max_length=255,
        blank=True,
        default="",
    )
    sort_order = models.IntegerField(
        _("Sort Order"),
        default=0,
        db_index=True,
    )
    category = models.CharField(
        _("Category"),
        max_length=100,
        blank=True,
        default="",
    )

    class Meta:
        """Meta options for OptionMetadataMixin."""

        abstract = True
