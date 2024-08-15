"""Forms for the users app."""

from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.forms import UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    """A form for creating new users. Includes all required fields plus a repeated password."""

    class Meta:
        """Meta class for CustomUserCreationForm."""

        model = User
        fields = ("username",)


class CustomUserChangeForm(UserChangeForm):
    """A form for updating users.

    Includes all the fields on the user, but replaces the password field with admin's password hash display field.
    """

    class Meta:
        """Meta class for CustomUserChangeForm."""

        model = User
        fields = ("username",)
