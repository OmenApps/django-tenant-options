# Generated by Django 4.2.15 on 2024-08-15 05:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions.text


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("example", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddConstraint(
            model_name="taskstatusselection",
            constraint=models.UniqueConstraint(
                models.F("tenant"), models.F("option"), name="example_taskstatusselection_name_val"
            ),
        ),
        migrations.AddConstraint(
            model_name="taskstatusoption",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("name"),
                models.F("tenant"),
                name="example_taskstatusoption_unique_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskstatusoption",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("option_type", "cu"), ("tenant__isnull", False)),
                    models.Q(("option_type", "dm"), ("tenant__isnull", True)),
                    models.Q(("option_type", "do"), ("tenant__isnull", True)),
                    _connector="OR",
                ),
                name="example_taskstatusoption_tenant_check",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskpriorityselection",
            constraint=models.UniqueConstraint(
                models.F("tenant"), models.F("option"), name="example_taskpriorityselection_name_val"
            ),
        ),
        migrations.AddConstraint(
            model_name="taskpriorityoption",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("name"),
                models.F("tenant"),
                name="example_taskpriorityoption_unique_name",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskpriorityoption",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("option_type", "cu"), ("tenant__isnull", False)),
                    models.Q(("option_type", "dm"), ("tenant__isnull", True)),
                    models.Q(("option_type", "do"), ("tenant__isnull", True)),
                    _connector="OR",
                ),
                name="example_taskpriorityoption_tenant_check",
            ),
        ),
    ]
