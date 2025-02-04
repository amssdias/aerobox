from django.contrib import admin

from apps.subscriptions.models.subscription import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "plan",
        "status",
        "start_date",
        "end_date",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
