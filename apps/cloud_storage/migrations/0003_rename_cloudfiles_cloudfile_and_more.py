# Generated by Django 4.2.15 on 2024-12-17 22:01

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "cloud_storage",
            "0002_remove_cloudfiles_cloud_stora_name_617d94_idx_and_more",
        ),
    ]

    operations = [
        migrations.RenameModel(
            old_name="CloudFiles",
            new_name="CloudFile",
        ),
        migrations.RenameIndex(
            model_name="cloudfile",
            new_name="cloud_stora_user_id_d2abd3_idx",
            old_name="cloud_stora_user_id_7db28d_idx",
        ),
        migrations.RenameIndex(
            model_name="cloudfile",
            new_name="cloud_stora_file_na_88e4b0_idx",
            old_name="cloud_stora_file_na_cdabf4_idx",
        ),
    ]