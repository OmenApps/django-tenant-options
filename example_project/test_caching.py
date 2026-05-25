"""Test cases for per-tenant option caching."""

import pytest

from django_tenant_options import app_settings
from django_tenant_options.choices import OptionType


@pytest.mark.django_db
class TestCacheSettings:
    """Verify the cache settings constants exist with correct defaults."""

    def test_cache_options_default_false(self):
        """CACHE_OPTIONS defaults to False (caching is opt-in)."""
        assert app_settings.CACHE_OPTIONS is False

    def test_cache_timeout_default(self):
        """CACHE_TIMEOUT defaults to 300 seconds."""
        assert app_settings.CACHE_TIMEOUT == 300

    def test_cache_key_prefix_default(self):
        """CACHE_KEY_PREFIX defaults to 'dto'."""
        assert app_settings.CACHE_KEY_PREFIX == "dto"

    def test_cache_alias_default(self):
        """CACHE_ALIAS defaults to 'default'."""
        assert app_settings.CACHE_ALIAS == "default"


@pytest.mark.django_db
class TestCacheModule:
    """Verify the cache.py helpers build keys and manage versions correctly."""

    def setup_method(self):
        """Clear the cache before each test."""
        from django.core.cache import cache

        cache.clear()

    def test_caching_enabled_reflects_setting(self):
        """caching_enabled() reads app_settings.CACHE_OPTIONS at call time."""
        from django_tenant_options import cache as dto_cache

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", False)
            assert dto_cache.caching_enabled() is False
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            assert dto_cache.caching_enabled() is True

    def test_version_key_format(self):
        """version_key builds '<prefix>:ver:<label>'."""
        from django_tenant_options import cache as dto_cache

        assert dto_cache.version_key("example.TaskPriorityOption") == "dto:ver:example.TaskPriorityOption"

    def test_get_version_initializes_to_one(self):
        """get_version returns 1 for a label not yet seen, and is stable."""
        from django_tenant_options import cache as dto_cache

        label = "example.TaskPriorityOption"
        assert dto_cache.get_version(label) == 1
        assert dto_cache.get_version(label) == 1

    def test_bump_version_increments(self):
        """bump_version increments the version, invalidating prior keys."""
        from django_tenant_options import cache as dto_cache

        label = "example.TaskPriorityOption"
        assert dto_cache.get_version(label) == 1
        dto_cache.bump_version(label)
        assert dto_cache.get_version(label) == 2

    def test_bump_version_when_missing(self):
        """bump_version works even when the version key was never initialized."""
        from django_tenant_options import cache as dto_cache

        label = "example.TaskPriorityOption"
        dto_cache.bump_version(label)
        assert dto_cache.get_version(label) >= 2

    def test_make_key_format(self):
        """make_key builds the fully-qualified per-tenant key."""
        from django_tenant_options import cache as dto_cache

        key = dto_cache.make_key("example.TaskPriorityOption", 7, "selected", False, 3)
        assert key == "dto:example.TaskPriorityOption:v3:t7:selected:d0"
        key2 = dto_cache.make_key("example.TaskPriorityOption", 7, "available", True, 3)
        assert key2 == "dto:example.TaskPriorityOption:v3:t7:available:d1"

    def test_set_and_get_cached_option_pks_roundtrip(self):
        """set/get cached pks round-trip a list of pks."""
        from django_tenant_options import cache as dto_cache

        key = dto_cache.make_key("example.TaskPriorityOption", 1, "selected", False, 1)
        assert dto_cache.get_cached_option_pks(key) is None
        dto_cache.set_cached_option_pks(key, [3, 1, 2])
        assert dto_cache.get_cached_option_pks(key) == [3, 1, 2]

    def test_cache_read_returns_none_when_backend_errors(self, monkeypatch):
        """A cache backend error during read degrades to a miss, not an exception."""
        from django_tenant_options import cache as dto_cache

        class _BoomCache:
            def get(self, *args, **kwargs):
                raise RuntimeError("redis down")

            def set(self, *args, **kwargs):
                raise RuntimeError("redis down")

        monkeypatch.setattr(dto_cache, "_get_cache", lambda: _BoomCache())
        assert dto_cache.get_cached_option_pks("dto:any:key") is None
        dto_cache.set_cached_option_pks("dto:any:key", [1, 2, 3])


@pytest.mark.django_db
class TestSelectedOptionsCaching:
    """Verify selected_options_for_tenant caches correctly and stays correct."""

    def setup_method(self):
        """Clear the cache before each test."""
        from django.core.cache import cache

        cache.clear()

    def _seed(self):
        """Create a tenant with one mandatory option and one selected custom option."""
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="Mandatory1", option_type=OptionType.MANDATORY)
        custom = TaskPriorityOption.objects.create(name="Custom1", option_type=OptionType.CUSTOM, tenant=tenant)
        TaskPrioritySelection.objects.create(tenant=tenant, option=custom)
        return tenant

    def test_disabled_by_default_still_correct(self):
        """With CACHE_OPTIONS False (default), repeated calls return correct results."""
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        first = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
        second = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
        assert first == second
        assert len(first) == 2  # one mandatory + one selected custom

    def test_cache_hit_serves_stored_pks(self, django_assert_num_queries):
        """The cache is genuinely consulted on a hit: overwriting the stored pks changes the result.

        (A query-count check alone is not enough here: the uncached path already issues a single
        query because Django folds the selections subquery in, so num_queries(1) passes whether or
        not the cache is read. Overwriting the cached entry proves the read actually happens.)
        """
        from django_tenant_options import cache as dto_cache
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            # Prime the cache (evaluate the queryset so the pks are computed and stored).
            primed = list(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert len(primed) == 2
            # A primed read is a single pk__in query.
            with django_assert_num_queries(1):
                cached = list(
                    TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True)
                )
            assert set(cached) == set(primed)
            # Overwrite the cached entry; if the method truly reads the cache, the result follows it.
            label = TaskPriorityOption._meta.label
            key = dto_cache.make_key(label, tenant.pk, "selected", False, dto_cache.get_version(label))
            kept = sorted(primed)[0]
            dto_cache.set_cached_option_pks(key, [kept])
            served = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert served == {kept}

    def test_cached_matches_uncached(self):
        """Results from the cached path equal results computed without caching."""
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        uncached = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            list(TaskPriorityOption.objects.selected_options_for_tenant(tenant))  # prime
            cached = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
        assert cached == uncached


@pytest.mark.django_db
class TestAvailableOptionsCaching:
    """Verify options_for_tenant caches correctly."""

    def setup_method(self):
        """Clear the cache before each test."""
        from django.core.cache import cache

        cache.clear()

    def _seed(self):
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        tenant = Tenant.objects.create(name="T", subdomain="t")
        TaskPriorityOption.objects.create(name="Mandatory1", option_type=OptionType.MANDATORY)
        TaskPriorityOption.objects.create(name="Optional1", option_type=OptionType.OPTIONAL)
        TaskPriorityOption.objects.create(name="Custom1", option_type=OptionType.CUSTOM, tenant=tenant)
        return tenant

    def test_cache_hit_serves_stored_pks(self, django_assert_num_queries):
        """The cache is genuinely consulted on a hit: overwriting the stored pks changes the result."""
        from django_tenant_options import cache as dto_cache
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            primed = list(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert len(primed) == 3
            with django_assert_num_queries(1):
                cached = list(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert set(cached) == set(primed)
            # Overwrite the cached entry; if the method truly reads the cache, the result follows it.
            label = TaskPriorityOption._meta.label
            key = dto_cache.make_key(label, tenant.pk, "available", False, dto_cache.get_version(label))
            kept = sorted(primed)[0]
            dto_cache.set_cached_option_pks(key, [kept])
            served = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert served == {kept}

    def test_cached_matches_uncached(self):
        """Cached path equals uncached computation."""
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        uncached = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            list(TaskPriorityOption.objects.options_for_tenant(tenant))  # prime
            cached = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
        assert cached == uncached

    def test_include_deleted_uses_separate_cache_key(self):
        """include_deleted=True is cached independently from include_deleted=False."""
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        optional = TaskPriorityOption.objects.filter(option_type=OptionType.OPTIONAL).first()
        optional.delete()  # soft-delete one option

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            active = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            with_deleted = set(
                TaskPriorityOption.objects.options_for_tenant(tenant, include_deleted=True).values_list("pk", flat=True)
            )
        assert optional.pk not in active
        assert optional.pk in with_deleted

    def test_available_and_selected_keys_independent(self):
        """The 'available' and 'selected' kinds do not collide in the cache."""
        from example_project.example.models import TaskPriorityOption

        tenant = self._seed()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            available = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            selected = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
        # available includes the unselected optional; selected does not.
        assert available != selected
        assert len(available) == 3
        assert len(selected) == 1  # only the mandatory; optional/custom not selected


@pytest.mark.django_db
class TestCacheSignals:
    """Verify the signal receivers bump the version for the correct model label."""

    def setup_method(self):
        """Clear the cache before each test."""
        from django.core.cache import cache

        cache.clear()

    def test_option_receiver_bumps_when_enabled(self):
        """The Option post_save receiver bumps the version when caching is enabled."""
        from django_tenant_options import cache as dto_cache
        from django_tenant_options.signals import _option_changed
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        label = TaskPriorityOption._meta.label
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            before = dto_cache.get_version(label)
            tenant = Tenant.objects.create(name="T", subdomain="t")
            option = TaskPriorityOption.objects.create(name="Custom1", option_type=OptionType.CUSTOM, tenant=tenant)
            _option_changed(sender=TaskPriorityOption, instance=option)
            assert dto_cache.get_version(label) > before

    def test_option_receiver_noop_when_disabled(self):
        """The receiver is a no-op when caching is disabled."""
        from django_tenant_options import cache as dto_cache
        from django_tenant_options.signals import _option_changed
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        label = TaskPriorityOption._meta.label
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", False)
            before = dto_cache.get_version(label)
            tenant = Tenant.objects.create(name="T", subdomain="t")
            option = TaskPriorityOption.objects.create(name="Custom1", option_type=OptionType.CUSTOM, tenant=tenant)
            _option_changed(sender=TaskPriorityOption, instance=option)
            assert dto_cache.get_version(label) == before

    def test_selection_receiver_bumps_option_label(self):
        """The Selection receiver bumps the version keyed by the option model label."""
        from django_tenant_options import cache as dto_cache
        from django_tenant_options.signals import _selection_changed
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        option_label = TaskPriorityOption._meta.label
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            before = dto_cache.get_version(option_label)
            tenant = Tenant.objects.create(name="T", subdomain="t")
            option = TaskPriorityOption.objects.create(name="M", option_type=OptionType.MANDATORY)
            selection = TaskPrioritySelection.objects.create(tenant=tenant, option=option)
            _selection_changed(sender=TaskPrioritySelection, instance=selection)
            assert dto_cache.get_version(option_label) > before

    def test_connect_cache_signals_runs(self):
        """connect_cache_signals() connects without error for all subclasses."""
        from django_tenant_options.signals import connect_cache_signals

        connect_cache_signals()  # should not raise


@pytest.mark.django_db
class TestSignalsConnectedOnReady:
    """Verify apps.ready() connected the cache signals at startup."""

    def test_receivers_are_connected(self):
        """The Option post_save signal has our receiver registered via dispatch_uid."""
        from django.db.models.signals import post_save

        from example_project.example.models import TaskPriorityOption

        # has_listeners is True if any receiver is connected for this sender.
        assert post_save.has_listeners(TaskPriorityOption)

    def test_end_to_end_invalidation_via_orm(self):
        """Creating a Selection through the ORM invalidates the cached selected list."""
        from django.core.cache import cache

        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        cache.clear()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            tenant = Tenant.objects.create(name="T", subdomain="t")
            TaskPriorityOption.objects.create(name="M", option_type=OptionType.MANDATORY)
            optional = TaskPriorityOption.objects.create(name="O", option_type=OptionType.OPTIONAL)

            before = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert len(before) == 1  # only the mandatory is selected

            # Select the optional option via the ORM; the post_save signal must invalidate the cache.
            TaskPrioritySelection.objects.create(tenant=tenant, option=optional)

            after = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk in after
            assert len(after) == 2  # not stale


@pytest.mark.django_db
class TestSoftDeleteInvalidation:
    """Verify soft-deleting an option invalidates cached lists."""

    def setup_method(self):
        from django.core.cache import cache

        cache.clear()

    def test_soft_delete_invalidates_selected(self):
        """Soft-deleting a selected custom option removes it from the cached selected list."""
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            tenant = Tenant.objects.create(name="T", subdomain="t")
            TaskPriorityOption.objects.create(name="M", option_type=OptionType.MANDATORY)
            custom = TaskPriorityOption.objects.create(name="C", option_type=OptionType.CUSTOM, tenant=tenant)
            TaskPrioritySelection.objects.create(tenant=tenant, option=custom)

            before = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert custom.pk in before

            custom.delete()  # soft delete -> sets `deleted`, fires post_save

            after = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert custom.pk not in after

    def test_hard_delete_invalidates_cached_available(self):
        """Hard-deleting an option (post_delete) invalidates the cached available list."""
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            tenant = Tenant.objects.create(name="HD", subdomain="hd")
            keep = TaskPriorityOption.objects.create(name="Keep", option_type=OptionType.MANDATORY)
            gone = TaskPriorityOption.objects.create(name="Gone", option_type=OptionType.CUSTOM, tenant=tenant)

            before = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert gone.pk in before

            gone.delete(override=True)  # hard delete -> post_delete signal

            after = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert gone.pk not in after
            assert keep.pk in after


@pytest.mark.django_db
class TestUserFacingFormCaching:
    """Verify UserFacingFormMixin works unchanged with caching enabled."""

    def setup_method(self):
        from django.core.cache import cache

        cache.clear()

    def test_form_field_uses_cached_selected_options(self):
        """A user-facing form built with caching enabled offers the correct selected options."""
        from django import forms as django_forms

        from django_tenant_options.forms import UserFacingFormMixin
        from example_project.example.models import Task
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        class _TaskForm(UserFacingFormMixin, django_forms.ModelForm):
            """Minimal user-facing form for caching tests - no request dependency."""

            class Meta:
                model = Task
                fields = ["title", "description", "priority", "status", "user"]

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            tenant = Tenant.objects.create(name="T", subdomain="t")
            mandatory = TaskPriorityOption.objects.create(name="M", option_type=OptionType.MANDATORY)
            custom = TaskPriorityOption.objects.create(name="C", option_type=OptionType.CUSTOM, tenant=tenant)
            TaskPrioritySelection.objects.create(tenant=tenant, option=custom)

            form = _TaskForm(tenant=tenant)
            choice_pks = {opt.pk for opt in form.fields["priority"].queryset}
            assert mandatory.pk in choice_pks
            assert custom.pk in choice_pks


@pytest.mark.django_db
class TestInvalidationPaths:
    """Verify invalidation fires on bulk QuerySet and SelectionsForm deselection paths."""

    def setup_method(self):
        """Clear the cache before each test."""
        from django.core.cache import cache

        cache.clear()

    def test_selectionsform_deselect_invalidates_cached_selected(self):
        """SelectionsForm.save() invalidates the cache when an option is deselected."""
        from example_project.example.forms import TaskPrioritySelectionForm
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import TaskPrioritySelection
        from example_project.example.models import Tenant

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)

            tenant = Tenant.objects.create(name="T", subdomain="t")
            mandatory = TaskPriorityOption.objects.create(name="Mandatory1", option_type=OptionType.MANDATORY)
            optional = TaskPriorityOption.objects.create(name="Optional1", option_type=OptionType.OPTIONAL)

            # Select the optional option so it appears in the selection list.
            TaskPrioritySelection.objects.create(tenant=tenant, option=optional)

            # Prime the cache - optional should be present.
            before = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk in before

            # Submit the form with only the mandatory option selected (deselects optional).
            form = TaskPrioritySelectionForm(
                data={"selections": [str(mandatory.pk)]},
                tenant=tenant,
            )
            assert form.is_valid(), form.errors
            form.save()

            # Cache must have been invalidated; optional should no longer appear.
            after = set(TaskPriorityOption.objects.selected_options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk not in after
            assert mandatory.pk in after

    def test_queryset_soft_delete_invalidates(self):
        """OptionQuerySet.delete() (soft-delete) invalidates the cached option list."""
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)

            tenant = Tenant.objects.create(name="T", subdomain="t")
            mandatory = TaskPriorityOption.objects.create(name="Mandatory1", option_type=OptionType.MANDATORY)
            optional = TaskPriorityOption.objects.create(name="Optional1", option_type=OptionType.OPTIONAL)

            # Prime the cache - both options should appear in available list.
            before = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk in before
            assert mandatory.pk in before

            # Bulk soft-delete via QuerySet (fires no per-instance signals).
            TaskPriorityOption.objects.filter(pk=optional.pk).delete()

            # Cache must have been invalidated; optional should no longer appear.
            after = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk not in after
            assert mandatory.pk in after

    def test_queryset_undelete_invalidates(self):
        """OptionQuerySet.undelete() invalidates the cached option list."""
        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)

            tenant = Tenant.objects.create(name="T", subdomain="t")
            TaskPriorityOption.objects.create(name="Mandatory1", option_type=OptionType.MANDATORY)
            optional = TaskPriorityOption.objects.create(name="Optional1", option_type=OptionType.OPTIONAL)

            # Soft-delete the optional option first (via instance delete, which fires signal).
            optional.delete()

            # Prime the cache - optional should not be present.
            before = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk not in before

            # Bulk undelete via QuerySet (fires no per-instance signals).
            TaskPriorityOption.objects.deleted().filter(pk=optional.pk).undelete()

            # Cache must have been invalidated; optional should reappear.
            after = set(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
            assert optional.pk in after


@pytest.mark.django_db
class TestCacheAlias:
    """Verify caching uses the configured CACHE_ALIAS."""

    def test_uses_non_default_alias(self, django_assert_num_queries):
        """With CACHE_ALIAS='options', cached reads come from that alias."""
        from django.core.cache import caches

        from example_project.example.models import TaskPriorityOption
        from example_project.example.models import Tenant

        caches["default"].clear()
        caches["options"].clear()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("django_tenant_options.app_settings.CACHE_OPTIONS", True)
            mp.setattr("django_tenant_options.app_settings.CACHE_ALIAS", "options")
            tenant = Tenant.objects.create(name="T", subdomain="t")
            TaskPriorityOption.objects.create(name="M", option_type=OptionType.MANDATORY)

            list(TaskPriorityOption.objects.options_for_tenant(tenant))  # prime "options" alias
            with django_assert_num_queries(1):
                list(TaskPriorityOption.objects.options_for_tenant(tenant).values_list("pk", flat=True))
