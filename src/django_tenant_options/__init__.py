"""Initialise the Django Tenant Options package."""

from django import get_version


def is_installed_less_than_version(version: str) -> bool:
    """Check if installed version of django is less than the version passed in the argument.

    Args:
        version (str): Version to compare with installed version.

    `version` should be in the format of `major.minor.patch` like `3.2.1`.
    """
    installed_version = get_version().split(".")
    version = version.split(".")
    if int(version[0]) < int(installed_version[0]):
        return True
    if int(version[0]) == int(installed_version[0]) and int(version[1]) < int(installed_version[1]):
        return True
    if (
        int(version[0]) == int(installed_version[0])
        and int(version[1]) == int(installed_version[1])
        and int(version[2]) < int(installed_version[2])
    ):
        return True
    return False
