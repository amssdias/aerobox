from django.contrib import admin

from apps.cloud_storage.models import CloudFiles


@admin.register(CloudFiles)
class CloudFilesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "path",
        "file_type",
        "user",
        "status",
    )
    list_per_page = 25
