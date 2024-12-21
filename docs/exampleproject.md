# Example Project

To demonstrate the functionality and usage of `django-tenant-options`, we have provided an [example project](https://github.com/OmenApps/django-tenant-options/example_project/) that showcases the key features of the package. The example project is a simple Django application that implements a basic _(not production-ready)_ multi-tenant architecture for SaaS with the ability to manage custom options for each tenant.

While the example project is not intended for production use, it serves as a reference for developers who want to understand how to integrate `django-tenant-options` into their own Django projects.

> 🟩 Note
>
> The example project is a simplified version of a real-world SaaS application and may not include all the features or best practices required for a production-ready application. It is intended to demonstrate the core functionality of `django-tenant-options` and provide a starting point for developers to build upon.

> 🟩 Note
>
> The example project uses SQLite as the default database for simplicity. For production use, you should consider using a more robust database like PostgreSQL.

> 🟩 Note
>
> We use [bootstrap](https://getbootstrap.com/) and [django-cripsy-forms](https://django-crispy-forms.readthedocs.io/en/latest/) for styling and form rendering in the example project, but these are not required for `django-tenant-options` to function.

## Example Project Walkthrough

### Core Components

#### 1. Multi-Tenant Architecture

The project implements a basic multi-tenant system with three main models:

- `User`: Extended Django user model with a foreign key to `Tenant`
- `Tenant`: Represents an organization with:
  - Name (e.g., "Mario's Project Management")
  - Subdomain (e.g., "marios-project-management")
- `Task`: The core business object with:
  - Title and description
  - Foreign keys to priority and status options
  - User association

![Screenshot of Tenant list view](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Tenant-List.png)

#### 2. Task Priority Management

The project demonstrates priority management using django-tenant-options:

##### Default Priority Options
```python
class TaskPriorityOption(AbstractOption):
    default_options = {
        "Critical": {"option_type": OptionType.OPTIONAL},
        "High": {"option_type": OptionType.MANDATORY},
        "Medium": {"option_type": OptionType.OPTIONAL},
        "Low": {"option_type": OptionType.MANDATORY},
    }
```

- Mandatory options ("High" and "Low") are always available to all tenants
- Optional options ("Critical" and "Medium") can be selected by tenants
- Tenants can create their own custom priority options

![Screenshot of Task Priority Options list](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Task-Priority-Options.png)

#### 3. Task Status Management

Similar to priorities, the project manages task statuses:

##### Default Status Options
```python
class TaskStatusOption(AbstractOption):
    default_options = {
        "New": {"option_type": OptionType.MANDATORY},
        "In Progress": {"option_type": OptionType.OPTIONAL},
        "Completed": {"option_type": OptionType.MANDATORY},
        "Archived": {"option_type": OptionType.MANDATORY},
    }
```

![Screenshot of Task Status Options list](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Task-Status-Options.png)

### Key Features Demonstrated

#### 1. Option Types
The project showcases the three types of options:

1. **Mandatory** (OptionType.MANDATORY):
   - Always selected for all tenants
   - Cannot be deselected
   - Example: "New" status, "High" priority

2. **Optional** (OptionType.OPTIONAL):
   - Available to all tenants
   - Can be selected/deselected
   - Example: "In Progress" status, "Critical" priority

3. **Custom** (OptionType.CUSTOM):
   - Created by specific tenants
   - Only available to the creating tenant
   - Example: "Super important" priority created by Ultimate Task Management

![Screenshot of option creation form showing option types](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Option-Create-Form.png)

#### 2. Selection Management

The project demonstrates how tenants can manage their selections:

1. **Viewing Available Options**:
   - Tenants see all mandatory options
   - Tenants see all optional options
   - Tenants see their own custom options

2. **Managing Selections**:
   - Select/deselect optional options
   - Manage custom options
   - Cannot deselect mandatory options

![Screenshot of selection management interface](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Task-Edit-Form.png)

#### 3. Form Integration

The project shows how to integrate django-tenant-options with forms:

1. **Task Creation/Update Forms**:
   ```python
   class TaskForm(UserFacingFormMixin, ModelForm):
       class Meta:
           model = Task
           fields = "__all__"
   ```
   - Only shows priority/status options available to the tenant
   - Automatically filters choices based on tenant selections

2. **Option Management Forms**:
   ```python
   class TaskPriorityOptionCreateForm(OptionCreateFormMixin, ModelForm):
       class Meta:
           model = TaskPriorityOption
           fields = ["name", "option_type", "tenant", "deleted"]
   ```
   - Handles creation of custom options
   - Manages option visibility and permissions

![Screenshot of task creation form](https://raw.githubusercontent.com/OmenApps/django-tenant-options/main/docs/media/django-tenant-options-Task-Create-Form.png)

#### 4. Soft Deletion

The example demonstrates soft deletion functionality:

- Options and selections can be soft-deleted
- Deleted items retain their data but become inactive
- Can be undeleted if needed
- Affects visibility in forms and querysets

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
   python manage.py loaddata testdata  # *See note below
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
