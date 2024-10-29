"""URLs for example app."""

from django.urls import path

from .views import home
from .views import task_create
from .views import task_list
from .views import task_priority_list
from .views import task_priority_option_create
from .views import task_priority_option_update
from .views import task_priority_selections_update
from .views import task_status_list
from .views import task_status_option_create
from .views import task_status_option_update
from .views import task_status_selections_update
from .views import task_update
from .views import tenant_create
from .views import tenant_list
from .views import tenant_update
from .views import user_tenant_update


app_name = "example_project.example"

urlpatterns = [
    path("", home, name="home"),
    path("user_tenant_update/<int:tenant_id>/", user_tenant_update, name="user_tenant_update"),
    path("task/create/", task_create, name="task_create"),
    path("task/list/", task_list, name="task_list"),
    path("task_update/<int:task_id>/", task_update, name="task_update"),
    path("tenant/list/", tenant_list, name="tenant_list"),
    path("tenant/create/", tenant_create, name="tenant_create"),
    path("tenant_update/<int:tenant_id>/", tenant_update, name="tenant_update"),
    path("task_priority/list/", task_priority_list, name="task_priority_list"),
    path("task_status/list/", task_status_list, name="task_status_list"),
    path(
        "task_priority_option/create/",
        task_priority_option_create,
        name="task_priority_option_create",
    ),
    path(
        "task_priority_option/update/<int:task_priority_option_id>/",
        task_priority_option_update,
        name="task_priority_option_update",
    ),
    path(
        "task_status_option/create/",
        task_status_option_create,
        name="task_status_option_create",
    ),
    path(
        "task_status_option/update/<int:task_status_option_id>/",
        task_status_option_update,
        name="task_status_option_update",
    ),
    path(
        "task_priority_selections/update/",
        task_priority_selections_update,
        name="task_priority_selections_update",
    ),
    path(
        "task_status_selections/update/",
        task_status_selections_update,
        name="task_status_selections_update",
    ),
]
