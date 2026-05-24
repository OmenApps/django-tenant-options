"""Serializers for exposing tenant options over Django REST Framework.

Requires ``djangorestframework``. Install via ``pip install django-tenant-options[drf]``.

The concrete Option/Selection model varies per project, so the serializers here
are not bound to a model. Either subclass them and set ``Meta.model``, or use the
provided factory functions to build a bound serializer dynamically.
"""

from rest_framework import serializers


OPTION_FIELDS = ["id", "name", "option_type", "deleted", "tenant"]
SELECTION_FIELDS = ["id", "tenant", "option", "deleted"]


class OptionSerializer(serializers.ModelSerializer):
    """Base serializer for AbstractOption subclasses.

    Subclass and set ``Meta.model`` to your concrete Option model::

        class PriorityOptionSerializer(OptionSerializer):
            class Meta(OptionSerializer.Meta):
                model = TaskPriorityOption
    """

    class Meta:
        """Default Meta. ``model`` must be set by a subclass."""

        model = None
        fields = OPTION_FIELDS


class SelectionSerializer(serializers.ModelSerializer):
    """Base serializer for AbstractSelection subclasses.

    Subclass and set ``Meta.model`` to your concrete Selection model.

    ``tenant`` is read-only because ``BaseSelectionViewSet.perform_create``
    injects it from ``get_tenant()`` - callers never supply it in the request body.
    """

    class Meta:
        """Default Meta. ``model`` must be set by a subclass."""

        model = None
        fields = SELECTION_FIELDS
        read_only_fields = ["tenant", "deleted"]


def option_serializer_factory(model, fields=None):
    """Build a ModelSerializer subclass bound to a concrete Option model.

    Args:
        model: A concrete AbstractOption subclass.
        fields: Optional list of field names. Defaults to OPTION_FIELDS.

    Returns:
        A ``ModelSerializer`` subclass with ``Meta.model`` set to ``model``.
    """
    meta = type(
        "Meta",
        (),
        {"model": model, "fields": list(fields) if fields is not None else list(OPTION_FIELDS)},
    )
    return type(f"{model.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": meta})


def selection_serializer_factory(model, fields=None):
    """Build a ModelSerializer subclass bound to a concrete Selection model.

    Args:
        model: A concrete AbstractSelection subclass.
        fields: Optional list of field names. Defaults to SELECTION_FIELDS.

    Returns:
        A ``ModelSerializer`` subclass with ``Meta.model`` set to ``model``.

    ``tenant`` and ``deleted`` are read-only because ``BaseSelectionViewSet.perform_create``
    injects the tenant from ``get_tenant()`` - callers never supply it in the request body.
    """
    meta = type(
        "Meta",
        (),
        {
            "model": model,
            "fields": list(fields) if fields is not None else list(SELECTION_FIELDS),
            "read_only_fields": ["tenant", "deleted"],
        },
    )
    return type(f"{model.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": meta})
