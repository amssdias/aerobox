# Generated by Django 4.2.15 on 2024-12-17 22:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cloud_storage", "0003_rename_cloudfiles_cloudfile_and_more"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="cloudfile",
            unique_together=set(),
        ),
    ]
