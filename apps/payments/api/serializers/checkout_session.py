from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class CheckoutSessionQuerySerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)

    def validate_session_id(self, value: str) -> str:
        if not value.startswith("cs_"):
            raise serializers.ValidationError(_("Invalid Stripe Checkout session ID."))
        return value


class CheckoutSessionInfoSerializer(serializers.Serializer):
    id = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    payment_status = serializers.CharField(allow_null=True)
    mode = serializers.CharField(allow_null=True)

    customer_email = serializers.EmailField(allow_null=True)

    amount_total = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField(allow_null=True)

    created = serializers.IntegerField(allow_null=True)
