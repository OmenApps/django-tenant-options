# Reference

## django_tenant_options

```{eval-rst}
.. automodule:: django_tenant_options
   :members:
```

## admin.py

```{eval-rst}
.. automodule:: django_tenant_options.admin
    :members:
```

## app_settings.py

```{eval-rst}
.. automodule:: django_tenant_options.app_settings
    :members:
```

## exceptions.py

```{eval-rst}
.. automodule:: django_tenant_options.exceptions
    :members:
```

## forms.py

```{eval-rst}
.. automodule:: django_tenant_options.forms
    :members:
```

## helpers.py

```{eval-rst}
.. automodule:: django_tenant_options.helpers
    :members:
```

## models.py

```{eval-rst}
.. automodule:: django_tenant_options.models
    :members:
```

## urls.py

```{eval-rst}
.. automodule:: django_tenant_options.urls
    :members:
```

## views.py

```{eval-rst}
.. automodule:: django_tenant_options.views
    :members:
```

## Commands

### `listoptions`

```{eval-rst}
.. autoclass:: django_tenant_options.management.commands.listoptions.Command
```

### `syncoptions`

```{eval-rst}
.. autoclass:: django_tenant_options.management.commands.syncoptions.Command
```

### `maketriggers`

```{eval-rst}
.. autoclass:: django_tenant_options.management.commands.maketriggers.Command
```

#### `maketriggers` Options

```{eval-rst}
.. option:: --app app_name

    (`str`) Specify a specific app to create migrations for. If not provided, migrations for all apps will be created.

.. option:: --model ModelName

    (`str`) Specify a specific model to create migrations for (format: app_label.ModelName). If not provided, migrations for all models will be created.

.. option:: --force

    (`bool`) Force creation of migrations even if the trigger already exists.

.. option:: --dry-run

    (`bool`) Simulate the migration creation process without writing any files. Use with --verbose to see the migration file content that would be created.

.. option:: --migration-dir directory

    (`str`) Specify the directory to write the migration files to. Defaults to the app's migrations directory.

.. option:: --db-vendor-override vendor

    (`str`) Specify the database vendor to use for the migration file. Overrides the default database vendor detection and settings. Must be one of 'postgresql', 'mysql', 'sqlite', or 'oracle'.

.. option:: --interactive

    (`bool`) Prompt for confirmation before creating each migration.",

.. option:: --verbose

    (`int`) Provide detailed output of the migration creation process.
```

### `removetriggers`

```{eval-rst}
.. autoclass:: django_tenant_options.management.commands.removetriggers.Command
```
