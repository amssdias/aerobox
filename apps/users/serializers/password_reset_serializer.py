from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        """Validates the email existence in the database."""
        if not User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(_("User with this email does not exist."))
        return email


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(max_length=128, write_only=True)
    new_password2 = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        password1 = data.get("new_password1")
        password2 = data.get("new_password2")

        if not password1 or not password2:
            raise serializers.ValidationError(_("Both passwords are required."))
        if password1 != password2:
            raise serializers.ValidationError(_("Passwords do not match."))

        try:
            validate_password(password1)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password1": e.messages})

        return data
