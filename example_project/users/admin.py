"""Admin module for custom user model."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserChangeForm
from .forms import CustomUserCreationForm
from .models import User


class CustomUserAdmin(UserAdmin):
    """Define admin model for custom User model with no email field."""

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    list_display = (
        "username",
        "tenant",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "username",
        "is_staff",
        "is_active",
    )
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("tenant",)}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "tenant",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
    search_fields = ("username", "tenant")
    ordering = ("username",)


admin.site.register(User, CustomUserAdmin)
