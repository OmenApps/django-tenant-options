# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Accessibility (WCAG 2.2 AA) improvements across the form layer, scaffolding, docs, and example templates: descriptive labels/help_text on the `delete` and `selections` fields, translatable option-type label suffixes, a human-readable `option_type_display` field on the DRF Option serializer, and a new opt-in `AccessibleFormMixin` that wires `aria-invalid`/`aria-describedby` onto errored fields.

### Changed

- The `deleted` field on `AbstractOption` and `AbstractSelection` now defines an explicit `verbose_name` ("Deleted at") and clearer `help_text`. **Migration required:** because these attributes are part of the field definition on the abstract base, every project with concrete Option/Selection models must run `python manage.py makemigrations` after upgrading to generate the resulting `AlterField` migration. No database schema change occurs; the migration only records the updated field metadata.
- `UserFacingFormMixin` no longer sets the invalid `readonly` attribute on disabled deleted-selection `<select>` widgets; it now sets `aria-disabled` and an explanatory `help_text` instead (the `disabled` attribute, which prevents resubmission, is retained).

## [2023.10.1]

Initial release!

### Added

- TBD

[unreleased]: https://github.com/jacklinke/django_tenant_options/compare/HEAD...HEAD
[2023.10.1]: https://github.com/jacklinke/django_tenant_options/releases/tag/2023.10.1
