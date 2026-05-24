"""Test cases for the optional REST Framework integration extras."""

import pytest


pytest.importorskip("rest_framework")


@pytest.mark.django_db
class TestRestFrameworkBootstrap:
    """Sanity checks that the DRF test module is collected and runnable."""

    def test_rest_framework_importable(self):
        """rest_framework must be importable because dev deps install it."""
        import rest_framework

        assert rest_framework.VERSION


@pytest.mark.django_db
class TestOptionSerializer:
    """Test cases for OptionSerializer and option_serializer_factory."""

    def test_factory_builds_bound_serializer_with_expected_fields(self):
        """The factory returns a ModelSerializer subclass bound to the model."""
        from django_tenant_options.choices import OptionType
        from django_tenant_options.contrib.rest_framework.serializers import option_serializer_factory
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        PriorityOptionSerializer = option_serializer_factory(TaskPriorityOption)

        tenant = Tenant.objects.create(name="T", subdomain="t")
        option = TaskPriorityOption.objects.create(
            name="Spicy",
            option_type=OptionType.CUSTOM,
            tenant=tenant,
        )

        serializer = PriorityOptionSerializer(option)
        data = serializer.data

        assert set(data.keys()) == {"id", "name", "option_type", "deleted", "tenant"}
        assert data["name"] == "Spicy"
        assert data["option_type"] == OptionType.CUSTOM
        assert data["tenant"] == tenant.id
        assert data["deleted"] is None

    def test_factory_accepts_custom_field_list(self):
        """Passing fields restricts the serialized output."""
        from django_tenant_options.contrib.rest_framework.serializers import option_serializer_factory
        from example_project.example.models import TaskPriorityOption

        Slim = option_serializer_factory(TaskPriorityOption, fields=["id", "name"])

        assert Slim.Meta.fields == ["id", "name"]
        assert Slim.Meta.model is TaskPriorityOption


@pytest.mark.django_db
class TestBaseOptionViewSet:
    """Test cases for BaseOptionViewSet list and selected actions."""

    def _make_viewset(self, tenant):
        """Build a concrete viewset subclass bound to TaskPriorityOption."""
        from django_tenant_options.contrib.rest_framework.serializers import option_serializer_factory
        from django_tenant_options.contrib.rest_framework.views import BaseOptionViewSet
        from example_project.example.models import TaskPriorityOption

        serializer_cls = option_serializer_factory(TaskPriorityOption)

        class PriorityOptionViewSet(BaseOptionViewSet):
            option_model = TaskPriorityOption
            serializer_class = serializer_cls

            def get_tenant(self):
                return tenant

        return PriorityOptionViewSet

    def test_get_tenant_not_implemented_by_default(self):
        """The base get_tenant must raise NotImplementedError with guidance."""
        from django_tenant_options.contrib.rest_framework.views import BaseOptionViewSet

        with pytest.raises(NotImplementedError):
            BaseOptionViewSet().get_tenant()

    def test_list_returns_available_options_for_tenant(self):
        """GET list returns all options available to the tenant."""
        from rest_framework.test import APIRequestFactory

        from django_tenant_options.choices import OptionType
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        other = Tenant.objects.create(name="O", subdomain="o")

        TaskPriorityOption.objects.create(name="Urgent", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Whenever", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Mine", option_type=OptionType.CUSTOM, tenant=tenant)
        TaskPriorityOption.objects.create(name="Theirs", option_type=OptionType.CUSTOM, tenant=other)

        viewset_cls = self._make_viewset(tenant)
        view = viewset_cls.as_view({"get": "list"})
        request = APIRequestFactory().get("/options/")
        response = view(request)
        response.render()

        names = {row["name"] for row in response.data}
        assert response.status_code == 200
        assert names == {"Urgent", "Whenever", "Mine"}
        assert "Theirs" not in names

    def test_selected_action_returns_only_selected_options(self):
        """The selected action returns mandatory + actively selected options."""
        from rest_framework.test import APIRequestFactory

        from django_tenant_options.choices import OptionType
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")

        mandatory = TaskPriorityOption.objects.create(name="Urgent", option_type=OptionType.MANDATORY)
        optional = TaskPriorityOption.objects.create(name="Whenever", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Skip", option_type=OptionType.OPTIONAL)
        TaskPrioritySelection.objects.create(tenant=tenant, option=optional)

        viewset_cls = self._make_viewset(tenant)
        view = viewset_cls.as_view({"get": "selected"})
        request = APIRequestFactory().get("/options/selected/")
        response = view(request)
        response.render()

        names = {row["name"] for row in response.data}
        assert response.status_code == 200
        assert mandatory.name in names
        assert optional.name in names
        assert "Skip" not in names


@pytest.mark.django_db
class TestBaseSelectionViewSet:
    """Test cases for BaseSelectionViewSet create and soft-delete behavior."""

    def _make_viewset(self, tenant):
        """Build a concrete selection viewset bound to TaskPrioritySelection."""
        from django_tenant_options.contrib.rest_framework.serializers import selection_serializer_factory
        from django_tenant_options.contrib.rest_framework.views import BaseSelectionViewSet
        from example_project.example.models import TaskPrioritySelection

        serializer_cls = selection_serializer_factory(TaskPrioritySelection)

        class PrioritySelectionViewSet(BaseSelectionViewSet):
            selection_model = TaskPrioritySelection
            serializer_class = serializer_cls

            def get_tenant(self):
                return tenant

        return PrioritySelectionViewSet

    def test_create_sets_tenant_for_selection(self):
        """POST creates a selection bound to the current tenant."""
        from rest_framework.test import APIRequestFactory

        from django_tenant_options.choices import OptionType
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        option = TaskPriorityOption.objects.create(name="Mine", option_type=OptionType.CUSTOM, tenant=tenant)

        viewset_cls = self._make_viewset(tenant)
        view = viewset_cls.as_view({"post": "create"})
        request = APIRequestFactory().post("/selections/", {"option": option.id}, format="json")
        response = view(request)
        response.render()

        assert response.status_code == 201
        selection = TaskPrioritySelection.objects.get(option=option)
        assert selection.tenant == tenant
        assert selection.deleted is None

    def test_destroy_soft_deletes_selection(self):
        """DELETE soft-deletes the selection (row remains, deleted is set)."""
        from rest_framework.test import APIRequestFactory

        from django_tenant_options.choices import OptionType
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        option = TaskPriorityOption.objects.create(name="Mine", option_type=OptionType.CUSTOM, tenant=tenant)
        selection = TaskPrioritySelection.objects.create(tenant=tenant, option=option)

        viewset_cls = self._make_viewset(tenant)
        view = viewset_cls.as_view({"delete": "destroy"})
        request = APIRequestFactory().delete(f"/selections/{selection.pk}/")
        response = view(request, pk=selection.pk)

        assert response.status_code == 204
        refreshed = TaskPrioritySelection.unscoped.get(pk=selection.pk)
        assert refreshed.deleted is not None

    def test_get_tenant_not_implemented_by_default(self):
        """The base get_tenant must raise NotImplementedError with guidance."""
        from django_tenant_options.contrib.rest_framework.views import BaseSelectionViewSet

        with pytest.raises(NotImplementedError):
            BaseSelectionViewSet().get_tenant()

    def test_create_invalid_option_returns_400_not_500(self):
        """Selecting another tenant's custom option returns 400 (model ValidationError -> DRF 400)."""
        from rest_framework.test import APIRequestFactory

        from django_tenant_options.choices import OptionType
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        other = Tenant.objects.create(name="O", subdomain="o")
        foreign = TaskPriorityOption.objects.create(name="Theirs", option_type=OptionType.CUSTOM, tenant=other)

        viewset_cls = self._make_viewset(tenant)
        view = viewset_cls.as_view({"post": "create"})
        request = APIRequestFactory().post("/selections/", {"option": foreign.id}, format="json")
        response = view(request)
        response.render()

        assert response.status_code == 400
        assert not TaskPrioritySelection.objects.filter(option=foreign, tenant=tenant).exists()


@pytest.mark.django_db
class TestBuildRouter:
    """Test cases for the build_router helper."""

    def test_build_router_registers_viewset(self):
        """build_router returns a DefaultRouter exposing the viewset's URLs."""
        from django_tenant_options.contrib.rest_framework.routers import build_router
        from django_tenant_options.contrib.rest_framework.serializers import option_serializer_factory
        from django_tenant_options.contrib.rest_framework.views import BaseOptionViewSet
        from example_project.example.models import TaskPriorityOption

        class PriorityOptionViewSet(BaseOptionViewSet):
            option_model = TaskPriorityOption
            serializer_class = option_serializer_factory(TaskPriorityOption)

        router = build_router("priorities", PriorityOptionViewSet)
        url_names = {pattern.name for pattern in router.urls}

        assert any("priorities" in name for name in url_names)
        assert len(router.urls) >= 1


@pytest.mark.django_db
class TestSchemaHelper:
    """Test cases for the soft-guarded drf-spectacular schema helper."""

    def test_maybe_extend_schema_returns_usable_decorator(self):
        """maybe_extend_schema returns a decorator that preserves the function."""
        from django_tenant_options.contrib.rest_framework.schema import maybe_extend_schema

        decorator = maybe_extend_schema(summary="List options")
        assert callable(decorator)

        @decorator
        def view(value):
            return value + 1

        assert callable(view)
        assert view(1) == 2

    def test_module_imports_without_error(self):
        """The schema module must import cleanly even with the soft guard."""
        import django_tenant_options.contrib.rest_framework.schema as schema

        assert hasattr(schema, "maybe_extend_schema")
        assert hasattr(schema, "SPECTACULAR_AVAILABLE")


@pytest.mark.django_db
class TestBoltAdapter:
    """Test cases for the optional django-bolt adapter."""

    def test_adapter_module_imports_without_django_bolt(self):
        """The adapter module must import even when django-bolt is absent."""
        import django_tenant_options.contrib.bolt.app as bolt_app

        assert hasattr(bolt_app, "register_option_routes")
        assert hasattr(bolt_app, "BOLT_AVAILABLE")

    def test_register_option_routes_with_bolt(self):
        """When django-bolt is installed, routes register on the app object."""
        pytest.importorskip("django_bolt")

        from django_tenant_options.choices import OptionType
        from django_tenant_options.contrib.bolt.app import register_option_routes
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="Mine", option_type=OptionType.CUSTOM, tenant=tenant)

        registered = []

        class FakeBoltApp:
            """Minimal stand-in matching the get(path) decorator contract."""

            def get(self, path):
                def decorator(func):
                    registered.append((path, func))
                    return func

                return decorator

        app = FakeBoltApp()
        register_option_routes(app, TaskPriorityOption, get_tenant=lambda request: tenant)

        paths = {path for path, _ in registered}
        assert any("available" in p for p in paths)
        assert any("selected" in p for p in paths)

    def test_register_option_routes_handlers_return_serialized_options(self):
        """Registered bolt route handlers return serialized option dicts for the tenant."""
        pytest.importorskip("django_bolt")

        from django_tenant_options.choices import OptionType
        from django_tenant_options.contrib.bolt.app import register_option_routes
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="BH", subdomain="bh")
        seeded = TaskPriorityOption.objects.create(name="Seeded", option_type=OptionType.MANDATORY)

        captured = []

        class FakeBoltApp:
            """Minimal stand-in matching the get(path) decorator contract."""

            def get(self, path):
                def decorator(func):
                    captured.append((path, func))
                    return func

                return decorator

        app = FakeBoltApp()
        register_option_routes(app, TaskPriorityOption, get_tenant=lambda request: tenant)

        # Both handlers were registered; call each and assert the seeded option appears.
        assert len(captured) == 2
        for path, func in captured:
            result = func(request=None)
            assert isinstance(result, list)
            names = [item["name"] for item in result]
            assert seeded.name in names, f"Handler for {path!r} did not include seeded option"
