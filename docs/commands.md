# Management Commands

`django-tenant-options` provides five management commands for managing options, validating configuration, and maintaining database triggers.

## Recommended workflow

When setting up or updating your options:

```bash
python manage.py validate_tenant_options  # Check configuration
python manage.py syncoptions              # Sync defaults to database
python manage.py maketriggers             # Generate trigger migrations (optional)
python manage.py migrate                  # Apply any new migrations
```

## `syncoptions`

Synchronizes the `default_options` defined in your Option models with the database.

```bash
python manage.py syncoptions
```

**When to run:**
- After `migrate`, whenever you've added or changed Option models
- After modifying `default_options` in any Option model
- As part of your deployment pipeline (after migrations)

**What it does:**
- Creates database records for any new default options
- Updates existing records if the option type has changed (e.g., from Optional to Mandatory)
- Does **not** delete options that have been removed from `default_options` -- those must be handled manually or via soft-delete

## `listoptions`

Lists all active options in the database, grouped by model.

```bash
python manage.py listoptions
```

Useful for quickly checking the current state of options after running `syncoptions` or when debugging.

## `validate_tenant_options`

Runs comprehensive validation checks on your `django-tenant-options` configuration.

```bash
python manage.py validate_tenant_options
```

**What it checks:**

For each Option model:
- Manager exists and inherits from `OptionManager`
- `selection_model` attribute is set
- `tenant_model` attribute is set
- `default_options` format is valid (only `MANDATORY` or `OPTIONAL` types)
- No duplicate default option names in the database
- Meta class inherits from `AbstractOption.Meta` (checks for expected constraints)

For each Selection model:
- Manager exists and inherits from `SelectionManager`
- `option_model` attribute is set
- `tenant_model` attribute is set
- No orphaned selections (active selections pointing to deleted options)
- Meta class inherits from `AbstractSelection.Meta` (checks for expected constraints)

**Exit codes:**
- `0` -- All checks passed (or only warnings)
- `1` -- Errors found

**CI/CD integration:**

Add to your CI pipeline to catch configuration issues early:

```yaml
# GitHub Actions example
- name: Validate tenant options
  run: python manage.py validate_tenant_options
```

## `maketriggers`

Creates Django migration files containing database triggers that enforce tenant-option consistency at the database level.

```bash
# Create triggers for all models
python manage.py maketriggers

# Then apply the migrations
python manage.py migrate
```

These triggers are a defense-in-depth measure. They prevent mismatches between a tenant and associated options at the database level, catching issues that could slip through if Django's validation layer is bypassed (e.g., direct SQL operations).

### Options

```bash
# Create triggers for a specific app
python manage.py maketriggers --app yourapp

# Create triggers for a specific model
python manage.py maketriggers --model yourapp.TaskPriorityOption

# Force recreation of existing triggers
python manage.py maketriggers --force

# Preview without making changes
python manage.py maketriggers --dry-run

# Preview with full detail
python manage.py maketriggers --dry-run --verbose

# Specify output directory for migration files
python manage.py maketriggers --migration-dir /path/to/migrations

# Override database vendor detection
python manage.py maketriggers --db-vendor-override postgresql

# Prompt before creating each migration
python manage.py maketriggers --interactive
```

| Flag | Description |
|------|-------------|
| `--app` | Limit to a specific Django app |
| `--model` | Limit to a specific model (`app_label.ModelName`) |
| `--force` | Recreate triggers even if they already exist |
| `--dry-run` | Simulate without writing files |
| `--verbose` | Show detailed output |
| `--migration-dir` | Custom directory for migration files |
| `--db-vendor-override` | Override database vendor (`postgresql`, `mysql`, `sqlite`, `oracle`) |
| `--interactive` | Prompt for confirmation before each migration |

### Supported databases

Triggers are supported for PostgreSQL, MySQL, SQLite, and Oracle. If you use a custom database backend (e.g., PostGIS), use `--db-vendor-override` to specify the underlying vendor.

## `removetriggers`

Creates migration files that remove previously created database triggers.

```bash
python manage.py removetriggers
python manage.py migrate
```

**When to use:**
- Before removing `django-tenant-options` from your project
- When troubleshooting trigger-related issues
- When switching database backends

## Common issues

### Trigger conflicts

If you encounter conflicts when recreating triggers:

```bash
python manage.py maketriggers --force
python manage.py migrate
```

### Options not appearing after deployment

Make sure `syncoptions` runs after `migrate` in your deployment:

```bash
python manage.py migrate
python manage.py syncoptions
```

### Validation failures in CI

Run `validate_tenant_options` locally first to see detailed output:

```bash
python manage.py validate_tenant_options
```

Fix any errors (missing managers, incorrect inheritance) before pushing.

## Further reading

- [Models Guide](models.md) -- Model configuration that these commands operate on
- [Configuration Reference](configuration.md) -- Settings that affect command behavior
- [Customization](customization.md) -- Database trigger details
