# Generated by Django 4.2.17 on 2025-02-28 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_alter_payment_payment_method_alter_payment_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="currency",
            field=models.CharField(default="eur", max_length=3),
        ),
    ]
