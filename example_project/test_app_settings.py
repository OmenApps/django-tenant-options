"""Test cases for the app_settings module."""

import pytest

from django_tenant_options.app_settings import ModelClassConfig
from django_tenant_options.app_settings import import_string


class TestImportString:
    """Test cases for the import_string function."""

    def test_valid_import(self):
        """Test importing a valid dotted path."""
        result = import_string("django.db.models.Model")
        from django.db import models

        assert result is models.Model

    def test_no_dots_raises_import_error(self):
        """Test that a path with no dots raises ImportError (ValueError path)."""
        with pytest.raises(ImportError, match="doesn't look like a module path"):
            import_string("nodots")

    def test_nonexistent_module_raises_import_error(self):
        """Test that a nonexistent module raises ImportError."""
        with pytest.raises(ImportError, match="does not exist"):
            import_string("nonexistent.module.Class")

    def test_missing_attribute_raises_import_error(self):
        """Test that a missing attribute in a valid module raises ImportError."""
        with pytest.raises(ImportError, match="does not define"):
            import_string("django.db.models.NonExistentClass")

    def test_import_real_class(self):
        """Test importing a real class by dotted path."""
        result = import_string("django.db.models.ForeignKey")
        from django.db import models

        assert result is models.ForeignKey


class TestModelClassConfig:
    """Test cases for the ModelClassConfig class."""

    def test_lazy_initialization(self):
        """Test that ModelClassConfig initializes lazily."""
        config = ModelClassConfig()
        assert config._initialized is False
        # Accessing a property triggers initialization
        _ = config.model_class
        assert config._initialized is True

    def test_default_model_class(self):
        """Test default model class is django.db.models.Model."""
        from django.db import models

        config = ModelClassConfig()
        assert config.model_class is models.Model

    def test_default_manager_class(self):
        """Test default manager class is django.db.models.Manager."""
        from django.db import models

        config = ModelClassConfig()
        assert config.manager_class is models.Manager

    def test_default_queryset_class(self):
        """Test default queryset class is django.db.models.QuerySet."""
        from django.db import models

        config = ModelClassConfig()
        assert config.queryset_class is models.QuerySet

    def test_default_foreignkey_class(self):
        """Test default foreignkey class is django.db.models.ForeignKey."""
        from django.db import models

        config = ModelClassConfig()
        assert config.foreignkey_class is models.ForeignKey

    def test_default_onetoonefield_class(self):
        """Test default onetoonefield class is django.db.models.OneToOneField."""
        from django.db import models

        config = ModelClassConfig()
        assert config.onetoonefield_class is models.OneToOneField

    def test_set_model_class_with_string(self):
        """Test setting model_class with a dotted string path."""
        config = ModelClassConfig()
        config.model_class = "django.db.models.Model"
        from django.db import models

        assert config.model_class is models.Model

    def test_set_model_class_with_class(self):
        """Test setting model_class with a direct class reference."""
        from django.db import models

        config = ModelClassConfig()
        config.model_class = models.Model
        assert config.model_class is models.Model

    def test_set_manager_class_with_string(self):
        """Test setting manager_class with a dotted string path."""
        config = ModelClassConfig()
        config.manager_class = "django.db.models.Manager"
        from django.db import models

        assert config.manager_class is models.Manager

    def test_set_queryset_class_with_string(self):
        """Test setting queryset_class with a dotted string path."""
        config = ModelClassConfig()
        config.queryset_class = "django.db.models.QuerySet"
        from django.db import models

        assert config.queryset_class is models.QuerySet

    def test_set_foreignkey_class_with_string(self):
        """Test setting foreignkey_class with a dotted string path."""
        config = ModelClassConfig()
        config.foreignkey_class = "django.db.models.ForeignKey"
        from django.db import models

        assert config.foreignkey_class is models.ForeignKey

    def test_set_onetoonefield_class_with_string(self):
        """Test setting onetoonefield_class with a dotted string path."""
        config = ModelClassConfig()
        config.onetoonefield_class = "django.db.models.OneToOneField"
        from django.db import models

        assert config.onetoonefield_class is models.OneToOneField

    def test_import_string_no_dots(self):
        """Test ModelClassConfig._import_string with no dots raises ImportError."""
        config = ModelClassConfig()
        with pytest.raises(ImportError, match="doesn't look like a module path"):
            config._import_string("nodots")

    def test_import_string_nonexistent_module(self):
        """Test ModelClassConfig._import_string with nonexistent module."""
        config = ModelClassConfig()
        with pytest.raises(ImportError, match="does not exist"):
            config._import_string("nonexistent.module.Class")

    def test_import_string_missing_attribute(self):
        """Test ModelClassConfig._import_string with missing attribute."""
        config = ModelClassConfig()
        with pytest.raises(ImportError, match="does not define"):
            config._import_string("django.db.models.NonExistentClass")

    def test_resolve_class_with_string(self):
        """Test _resolve_class with a string dotted path."""
        from django.db import models

        config = ModelClassConfig()
        result = config._resolve_class("django.db.models.Model")
        assert result is models.Model

    def test_resolve_class_with_class(self):
        """Test _resolve_class with a direct class reference."""
        from django.db import models

        config = ModelClassConfig()
        result = config._resolve_class(models.Model)
        assert result is models.Model

    def test_setter_marks_initialized(self):
        """Test that setters mark config as initialized."""
        from django.db import models

        config = ModelClassConfig()
        assert config._initialized is False
        config.model_class = models.Model
        assert config._initialized is True

    def test_ensure_initialized_idempotent(self):
        """Test that _ensure_initialized is idempotent."""
        config = ModelClassConfig()
        config._ensure_initialized()
        first_model = config._model_class
        config._ensure_initialized()
        assert config._model_class is first_model
