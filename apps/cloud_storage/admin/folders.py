from django.contrib import admin

from apps.cloud_storage.models import Folder


@admin.register(Folder)
class FoldersAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "parent",
        "user",
    )
    list_per_page = 25
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("user",)
    search_fields = ("name",)
