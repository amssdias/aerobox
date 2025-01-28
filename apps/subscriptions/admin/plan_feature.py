from django.contrib import admin

from apps.subscriptions.models import PlanFeature


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "plan",
        "feature",
    )
    list_filter = (
        "plan",
        "feature",
    )
