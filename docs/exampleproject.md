# The Example Project

To demonstrate the functionality and usage of `django-tenant-options`, we have provided an [example project](https://github.com/OmenApps/django-tenant-options/example_project/) that showcases the key features of the package. The example project is a simple Django application that implements a basic *(not production-ready)* multi-tenant architecture for SaaS with the ability to manage custom options for each tenant.

While the example project is not intended for production use, it serves as a reference for developers who want to understand how to integrate `django-tenant-options` into their own Django projects.

## Basic Overview

The example project demonstrates how to set up a multi-tenant application with custom options using `django-tenant-options`. It includes the following features:

- **User Model**: A basic `User` model for authentication purposes, with a ForeignKey to the `Tenant` model.
- **Tenant Model**: A simple `Tenant` model representing the tenants (businesses or organizations) in the SaaS application.
- **Task Model**: A model representing tasks that belong to each user.
- **Option Models**: Default and custom options for a Tasks `priority` and `status`.
- **Selection Models**: A model that stores the selected `priority` and `status` options selected by each tenant.
- **Admin Interface**: Custom admin interfaces for managing tenants, options, and selections.
- **Forms**: Custom forms for enabling Tenants to create, update, and select options.
- **Views and Templates**: Basic views and templates for displaying tenant-specific options.

> 🟩 Note
>
> The example project is a simplified version of a real-world SaaS application and may not include all the features or best practices required for a production-ready application. It is intended to demonstrate the core functionality of `django-tenant-options` and provide a starting point for developers to build upon.

> 🟩 Note
>
> The example project uses SQLite as the default database for simplicity. For production use, you should consider using a more robust database like PostgreSQL.

> 🟩 Note
>
> We use [bootstrap](https://getbootstrap.com/) and [django-cripsy-forms](https://django-crispy-forms.readthedocs.io/en/latest/) for styling and form rendering in the example project, but these are not required for `django-tenant-options` to function.

## Model Diagram

The following diagram illustrates the relationships between the models in the example project:

![Model Diagram](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Relationships-Detailed.png)

## Installation

To install the example project, follow these steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/OmenApps/django-tenant-options.git
    ```

2. Navigate to the django-tenant-options directory:

    ```bash
    cd django-tenant-options/
    ```

3. Create a virtual environment:

    ```bash
    python3 -m venv .venv
    ```

4. Activate the virtual environment:

    ```bash
    source .venv/bin/activate
    ```

5. Install poetry if you haven't already:

    ```bash
    pip install poetry
    ```

6. Then install the required packages:

    ```bash
    poetry install --with dev
    ```

7. Set up the example project:

    ```bash
    python manage.py migrate
    python manage.py loaddata testdata.json  # *See note below
    ```

The provided fixtures include the following:
- A superuser with the username `admin`, password `pass`, and initial membership in the `Mario's Project Management` tenant.
- Three tenants: 1. `Mario's Project Management`, 2. `Ultimate Task Management`, and 3. `Projects R Us`.
- Several `priority` and `status` options and initial selections for each tenant.

> 🟩 Note
>
> Instead of using the `loaddata` command, in a real project you would use the `syncoptions` command to sync the default options from the model definitions with the database.

8. Create Triggers (recommended):

    ```bash
    python manage.py maketriggers
    python manage.py migrate
    ```

9. Run the development server:

    ```bash
    python manage.py runserver
    ```

10. To keep things as simple as possible, we have not implemented login or logout views. Login via the admin panel in your browser at `http://127.0.0.1:8000/admin/`, after which you may access the example project itself at `http://127.0.0.1:8000/`.
