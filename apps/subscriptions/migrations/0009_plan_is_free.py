# Generated by Django 4.2.17 on 2025-06-15 14:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0008_alter_plan_description_alter_plan_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="is_free",
            field=models.BooleanField(default=False),
        ),
    ]
