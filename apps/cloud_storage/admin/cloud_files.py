from django.contrib import admin

from apps.cloud_storage.models import CloudFile


@admin.register(CloudFile)
class CloudFilesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_name",
        "folder",
        "path",
        "user",
        "deleted_at",
        "status",
    )
    list_per_page = 25
    readonly_fields = (
        "size",
        "s3_key",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    raw_id_fields = ("user",)