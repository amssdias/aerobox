# Generated by Django 4.2.17 on 2025-02-25 21:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0005_plan_stripe_price_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="billing_cycle",
            field=models.CharField(
                choices=[("month", "Monthly"), ("year", "Yearly")], max_length=10
            ),
        ),
    ]
