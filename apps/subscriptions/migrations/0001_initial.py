# Generated by Django 4.2.17 on 2025-01-28 21:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "monthly_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "yearly_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "trial_duration_days",
                    models.PositiveIntegerField(
                        blank=True,
                        default=14,
                        help_text="Duration of the free trial period in days",
                        null=True,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
