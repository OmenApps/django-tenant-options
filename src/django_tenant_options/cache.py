"""Per-tenant option caching helpers for django-tenant-options.

This module implements an opt-in cache for per-tenant option lists. Invalidation uses a
namespace-version scheme: each Option model has an integer "version" stored in the cache, and
every per-tenant key embeds that version. Bumping the version (on save/delete signals) makes all
previously cached keys for that model unreachable without enumerating them.

All settings are read from ``django_tenant_options.app_settings`` AT CALL TIME so that tests can
monkeypatch ``app_settings.CACHE_OPTIONS`` (and friends) and have the change take effect.
"""

import logging

from django.core.cache import caches

from django_tenant_options import app_settings


logger = logging.getLogger("django_tenant_options")


def caching_enabled() -> bool:
    """Return whether per-tenant option caching is currently enabled."""
    return bool(app_settings.CACHE_OPTIONS)


def _get_cache():
    """Resolve the configured Django cache backend at call time."""
    return caches[app_settings.CACHE_ALIAS]


def version_key(option_model_label: str) -> str:
    """Return the cache key that holds the namespace version for an Option model label."""
    return f"{app_settings.CACHE_KEY_PREFIX}:ver:{option_model_label}"


def get_version(option_model_label: str) -> int:
    """Return the current namespace version for an Option model label.

    Initializes the version to 1 (via ``cache.add``) if it is not yet present.
    """
    cache = _get_cache()
    key = version_key(option_model_label)
    # add() only sets the value if the key is absent, avoiding clobbering a concurrent writer.
    cache.add(key, 1, None)
    version = cache.get(key, 1)
    return int(version)


def bump_version(option_model_label: str) -> int:
    """Increment the namespace version for an Option model label, invalidating its cached lists.

    Uses ``cache.incr`` when the key exists; falls back to ``cache.add`` if the key is missing
    (some backends raise ValueError when incrementing an absent key).
    """
    cache = _get_cache()
    key = version_key(option_model_label)
    try:
        new_version = cache.incr(key)
    except ValueError:
        # Key was missing or expired; start a fresh namespace at version 2 so any stale key
        # built against an implicit version 1 is no longer reachable.
        cache.add(key, 2, None)
        new_version = cache.get(key, 2)
    logger.debug("Bumped cache version for %s to %s", option_model_label, new_version)
    return int(new_version)


def make_key(
    option_model_label: str,
    tenant_pk,
    kind: str,
    include_deleted: bool,
    version: int,
) -> str:
    """Build the fully-qualified per-tenant cache key.

    Args:
        option_model_label: e.g. "example.TaskPriorityOption".
        tenant_pk: the tenant primary key.
        kind: "available" (options_for_tenant) or "selected" (selected_options_for_tenant).
        include_deleted: whether deleted options are included.
        version: the current namespace version for the model label.
    """
    prefix = app_settings.CACHE_KEY_PREFIX
    return f"{prefix}:{option_model_label}:v{version}:t{tenant_pk}:{kind}:d{int(include_deleted)}"


def safe_bump_version(option_model_label: str) -> None:
    """Invalidate cached lists for an option model, resilient to cache-backend failure.

    No-op when caching is disabled. Any cache-backend error is logged and swallowed so a
    failed invalidation never breaks the write (save/delete) that triggered it.
    """
    if not caching_enabled():
        return
    try:
        bump_version(option_model_label)
    except Exception:  # pragma: no cover - cache backend failure must not break writes
        logger.warning("Cache invalidation failed for %s", option_model_label, exc_info=True)


def get_cached_option_pks(key: str):
    """Return the cached list of option pks for a key, or None on a miss or backend error."""
    try:
        return _get_cache().get(key)
    except Exception:
        logger.warning("DTO cache read failed for key=%s; treating as miss", key, exc_info=True)
        return None


def set_cached_option_pks(key: str, pks) -> None:
    """Store a list of option pks under a key; no-op on a backend error."""
    try:
        _get_cache().set(key, list(pks), app_settings.CACHE_TIMEOUT)
    except Exception:
        logger.warning("DTO cache write failed for key=%s; skipping", key, exc_info=True)
