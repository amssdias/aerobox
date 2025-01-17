from django.contrib import admin

from apps.subscriptions.models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_active",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
