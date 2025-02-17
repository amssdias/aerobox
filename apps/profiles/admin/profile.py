from django.contrib import admin

from apps.profiles.models.profile import Profile


@admin.register(Profile)
class CloudFilesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user"
    )
