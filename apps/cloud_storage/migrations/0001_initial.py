# Generated by Django 4.2.17 on 2025-01-02 22:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CloudFile",
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
                (
                    "file_name",
                    models.CharField(
                        help_text="The intended name of the file to be stored in S3.",
                        max_length=255,
                    ),
                ),
                (
                    "path",
                    models.CharField(
                        help_text="The S3 path where the file is stored.",
                        max_length=255,
                    ),
                ),
                (
                    "size",
                    models.BigIntegerField(
                        help_text="The size of the file in bytes. This can be updated after the file is uploaded."
                    ),
                ),
                (
                    "content_type",
                    models.CharField(
                        help_text="The MIME type of the file (e.g., 'image/jpeg', 'application/pdf').",
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("uploaded", "Uploaded"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        help_text="The current status of the file upload process.",
                        max_length=8,
                    ),
                ),
                (
                    "checksum",
                    models.CharField(
                        blank=True,
                        help_text="A checksum or hash (e.g., MD5, SHA256) to verify the integrity of the uploaded file.",
                        max_length=64,
                        null=True,
                    ),
                ),
                (
                    "file_url",
                    models.URLField(
                        blank=True,
                        help_text="The URL to access the file in S3. This is generated after the file is uploaded.",
                        max_length=1024,
                        null=True,
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        help_text="Any error message encountered during the file upload process.",
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        help_text="Additional metadata related to the file, stored as a JSON object.",
                        null=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The user who uploaded the file (owner).",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Cloud File",
                "verbose_name_plural": "Cloud Files",
                "indexes": [
                    models.Index(
                        fields=["user"], name="cloud_stora_user_id_d2abd3_idx"
                    ),
                    models.Index(
                        fields=["file_name"], name="cloud_stora_file_na_88e4b0_idx"
                    ),
                ],
            },
        ),
    ]
