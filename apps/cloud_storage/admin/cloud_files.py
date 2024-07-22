from django.contrib import admin

from apps.cloud_storage.models import CloudFiles


@admin.register(CloudFiles)
class CloudFilesAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "file_uploaded")
    list_per_page = 25
