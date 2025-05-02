from django.contrib import admin

from apps.subscriptions.models import PlanFeature


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_plan_name",
        "feature",
    )
    list_filter = (
        "feature",
    )
    raw_id_fields = ("plan",)

    def get_plan_name(self, obj):
        return obj.plan.name.get("en", "Unnamed Plan")

    get_plan_name.short_description = "Plan Name"
    get_plan_name.admin_order_field = "plan"
