# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [2026.5.3] - 2026-05-25

### Added

- Added `default_options_allow_empty = True` for Option models that intentionally define no system defaults, so diagnostics report an info instead of a warning.
- Added `SelectionsForm.multiple_choice_field_kwargs`, allowing forms to pass extra constructor kwargs such as `group_by="category"` to custom multiple-choice fields.

### Changed

- `syncoptions` now persists `description`, `help_text`, `sort_order`, and `category` values from `default_options` when the concrete Option model defines those fields.
- Cache helper failures now degrade to cache misses or write no-ops and log a warning instead of raising into request code.

## [2026.5.2]

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
[2026.5.3]: https://github.com/jacklinke/django_tenant_options/releases/tag/2026.5.3
[2026.5.2]: https://github.com/jacklinke/django_tenant_options/releases/tag/2026.5.2
[2023.10.1]: https://github.com/jacklinke/django_tenant_options/releases/tag/2023.10.1
