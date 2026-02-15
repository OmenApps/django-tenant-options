"""Initialise the Django Tenant Options package."""

from django import get_version


def is_installed_less_than_version(version: str) -> bool:
    """Check if installed version of django is less than the version passed in the argument.

    Args:
        version (str): Version to compare with installed version.

    `version` should be in the format of `major.minor.patch` like `3.2.1`.
    """
    installed_parts = get_version().split(".")
    version_parts = version.split(".")
    if int(installed_parts[0]) < int(version_parts[0]):
        return True
    if int(installed_parts[0]) == int(version_parts[0]) and int(installed_parts[1]) < int(version_parts[1]):
        return True
    if (
        int(installed_parts[0]) == int(version_parts[0])
        and int(installed_parts[1]) == int(version_parts[1])
        and int(installed_parts[2]) < int(version_parts[2])
    ):
        return True
    return False
