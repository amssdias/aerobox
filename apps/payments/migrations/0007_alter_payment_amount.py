# Generated by Django 4.2.17 on 2025-03-01 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0006_alter_payment_payment_date_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]
