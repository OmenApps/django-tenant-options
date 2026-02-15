# Contributor Guide

Thank you for your interest in improving this project.
This project is open-source under the [MIT license] and
welcomes contributions in the form of bug reports, feature requests, and pull requests.

Here is a list of important resources for contributors:

- [Source Code]
- [Documentation]
- [Issue Tracker]
- [Code of Conduct]

[mit license]: https://opensource.org/licenses/MIT
[source code]: https://github.com/OmenApps/django-tenant-options
[documentation]: https://django-tenant-options.readthedocs.io/
[issue tracker]: https://github.com/OmenApps/django-tenant-options/issues

## How to report a bug

Report bugs on the [Issue Tracker].

When filing an issue, make sure to answer these questions:

- Which operating system and Python version are you using?
- Which version of this project are you using?
- What did you do?
- What did you expect to see?
- What did you see instead?

The best way to get your bug fixed is to provide a test case,
and/or steps to reproduce the issue.

## How to request a feature

Request features on the [Issue Tracker].

## How to set up your development environment

You need Python 3.11+ and the following tools:

- [uv]
- [Nox]

Install the package with development requirements:

```console
$ uv sync --extra=dev
```

[uv]: https://docs.astral.sh/uv/
[nox]: https://nox.thea.codes/

## Running the example project

The repository includes an example project that demonstrates the package's functionality:

```console
$ uv run python manage.py makemigrations
$ uv run python manage.py migrate
$ uv run python manage.py loaddata testdata
$ uv run python manage.py syncoptions
$ uv run python manage.py runserver
```

Log in via the admin at `http://127.0.0.1:8000/admin/` (username: `admin`, password: `pass`), then access the example project at `http://127.0.0.1:8000/`.

## How to test the project

Run the full test suite:

```console
$ uv run nox -s tests
```

Run tests with specific Python and Django versions:

```console
$ uv run nox -s tests -- python="3.12" django="5.1"
```

Run a specific test file:

```console
$ uv run nox -s tests -- example_project/test_models.py
```

Run tests directly with pytest and coverage:

```console
$ uv run coverage run -m pytest -vv
$ uv run coverage report
```

List the available Nox sessions:

```console
$ uv run nox --list-sessions
```

## Code quality

Run all pre-commit hooks:

```console
$ uv run nox -s pre-commit -- run --all-files
```

The project uses:

- **ruff** for formatting and linting (120 character line length)
- **bandit** for security checks

Install pre-commit hooks to run checks automatically on each commit:

```console
$ uv run nox -s pre-commit -- install
```

## Building documentation

Build docs once:

```console
$ uv run nox -s docs-build
```

Build and serve with live reload:

```console
$ uv run nox -s docs
```

## How to submit changes

Open a [pull request] to submit changes to this project.

Your pull request needs to meet the following guidelines for acceptance:

- The Nox test suite must pass without errors and warnings.
- Include unit tests. This project maintains high code coverage.
- If your changes add functionality, update the documentation accordingly.

Feel free to submit early, though -- we can always iterate on this.

It is recommended to open an issue before starting work on anything.
This will allow a chance to talk it over with the owners and validate your approach.

[pull request]: https://github.com/OmenApps/django-tenant-options/pulls

## Common issues

### Database trigger conflicts

If you encounter trigger conflicts during development:

```console
$ uv run python manage.py maketriggers --force
$ uv run python manage.py migrate
```

### Pre-commit hook failures

```console
$ uv run pre-commit run --all-files
$ uv run pre-commit autoupdate
```

### Documentation build errors

```console
$ rm -rf docs/_build
$ uv run nox -s docs-build
```

<!-- github-only -->

[code of conduct]: CODE_OF_CONDUCT.md
