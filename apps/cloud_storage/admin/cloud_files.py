from django.contrib import admin

from apps.cloud_storage.models import CloudFile


@admin.register(CloudFile)
class CloudFilesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_name",
        "path",
        "content_type",
        "user",
        "status",
    )
    list_per_page = 25
    readonly_fields = (
        "size",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    raw_id_fields = ("user",)