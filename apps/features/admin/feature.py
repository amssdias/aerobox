from django.contrib import admin

from apps.features.models.feature import Feature


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "is_active"
    )
