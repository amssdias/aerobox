from django.contrib import admin

from apps.cloud_storage.models import CloudFile


@admin.register(CloudFile)
class CloudFilesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "file_name",
        "path",
        "file_type",
        "user",
        "status",
    )
    list_per_page = 25
