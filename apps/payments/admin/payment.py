from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "payment_date",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
