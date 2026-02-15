# Concepts

This page explains the ideas behind `django-tenant-options` -- why it works the way it does, and how the pieces fit together. Read this before diving into the how-to guides if you want to understand the "why" behind the design decisions.

## The problem

In a SaaS application, tenants (organizations, teams, accounts) often need to customize form options. A project management tool might need different task priorities for different companies. An HR system might need different job title categories per department.

The naive approaches each have drawbacks:

- **CharField with TextChoices**: One fixed set of options for everyone. Adding options requires code changes and deployments.
- **ManyToManyField with a custom model**: No built-in distinction between global defaults and tenant-specific options. Complex to manage.
- **JSON fields**: No schema validation, no referential integrity, can't query efficiently.
- **Custom tables per tenant**: Schema complexity, migration nightmares, performance issues.

`django-tenant-options` solves this by providing a structured, flexible system where developers define global defaults and tenants can customize what's available to their users.

## The two-model pattern

Every set of customizable options in `django-tenant-options` is defined by a pair of models:

1. **Option model** -- Stores every available option: mandatory defaults, optional defaults, and tenant-created custom options.
2. **Selection model** -- A through model that records which options each tenant has currently enabled.

Why two models instead of one? Separation of concerns. The Option model is the catalog of everything that *could* be chosen. The Selection model tracks what each tenant has *actually* chosen. This makes it straightforward to:

- Add new default options without affecting existing tenant selections
- Let tenants enable/disable optional defaults independently
- Let tenants create custom options that only they can see
- Soft-delete options without breaking existing records that reference them

## Option types

Every option has one of three types:

### Mandatory (`OptionType.MANDATORY`)

Always available to all tenants. Cannot be disabled. Every tenant's users will see these options in forms.

**Use for**: Core options that every tenant needs. In a project management tool, "High" and "Low" priorities might be mandatory -- every team needs at least these.

### Optional (`OptionType.OPTIONAL`)

Available to all tenants, but each tenant decides whether to enable it. A tenant admin can select or deselect these through a selections form.

**Use for**: Common options that not every tenant needs. "Critical" priority might be useful for some teams but unnecessary clutter for others.

### Custom (`OptionType.CUSTOM`)

Created by a specific tenant for their own use. Only visible to the tenant that created it. Other tenants never see it.

**Use for**: Tenant-specific needs you can't anticipate. One company might need a "Blocked by Legal" status. Another might want an "Awaiting Client Feedback" priority.

## How options flow through the system

Here's the lifecycle, from developer to end user:

1. **Developer defines defaults** -- You specify `default_options` on your Option model with names and types (mandatory or optional).

2. **Database sync** -- Running `python manage.py syncoptions` creates the actual database records for these defaults. Run this after migrations or whenever you change `default_options`.

3. **Tenant admin manages selections** -- A tenant admin uses a `SelectionsForm` to choose which optional defaults to enable. Mandatory options are always included automatically. They can also create custom options through an `OptionCreateFormMixin` form.

4. **End user sees filtered options** -- When an end user fills out a form using `UserFacingFormMixin`, the form automatically shows only the options that the user's tenant has selected. Mandatory options, enabled optional options, and the tenant's custom options all appear. Nothing else.

## Soft deletes

Both Option and Selection models use soft deletes. When you "delete" an option, it isn't removed from the database -- instead, a `deleted` timestamp is set on the record.

This matters for data integrity. If a task has a "Critical" priority and that priority option gets deleted, the task still has a valid foreign key pointing at the option record. Without soft deletes, you'd face cascading deletes or broken references.

- `.delete()` sets the `deleted` timestamp (soft delete)
- `.delete(override=True)` performs an actual database deletion (hard delete)
- `.undelete()` clears the `deleted` timestamp, restoring the record
- QuerySets provide `.active()` and `.deleted()` filters

## The metaclass system

When you inherit from `AbstractOption` or `AbstractSelection`, custom metaclasses automatically add fields and relationships to your model:

- A `tenant` ForeignKey pointing to your tenant model
- An `associated_tenants` ManyToManyField (on Option models) through the Selection model
- An `option` ForeignKey (on Selection models) pointing to the paired Option model

You don't need to understand the metaclass internals. Just know that when you set `tenant_model` and `selection_model` (or `option_model`) on your concrete models, the metaclasses use those to wire up the relationships. This is why those class attributes are required.

## Managers and querysets

The package provides custom managers and querysets with methods tailored to common operations:

- `OptionManager` with methods like `create_for_tenant()`, `create_mandatory()`, and `create_optional()`
- `OptionQuerySet` with methods like `options_for_tenant()`, `selected_options_for_tenant()`, `active()`, and `deleted()`
- An `unscoped` manager on every model that returns all records, including soft-deleted ones

Your concrete models automatically get these managers. If you define custom managers, they must inherit from `OptionManager` or `SelectionManager` -- otherwise the package's filtering won't work. Django system checks will warn you if this isn't set up correctly.

## Database triggers

For defense in depth, `django-tenant-options` can generate database triggers that enforce tenant-option consistency at the database level. This prevents mismatches that could occur from direct SQL queries or bugs that bypass Django's validation layer.

Triggers are optional but recommended for production. Generate them with `python manage.py maketriggers`, then apply with `python manage.py migrate`.

## Further reading

- [Terminology](terminology.md) -- Precise definitions for all key terms
- [Models Guide](models.md) -- How to define Option and Selection models
- [Forms Guide](forms.md) -- How to build forms that respect tenant selections
- [Configuration Reference](configuration.md) -- All available settings
