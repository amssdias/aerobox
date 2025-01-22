from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.users.serializers.password_reset_serializer import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from apps.users.tasks.email_tasks import send_password_reset_email
from config.api_docs.custom_extensions import api_users_tag


@api_users_tag()
class CustomPasswordResetView(GenericAPIView):
    """
    Sends a password reset link to the user's email.

    The link includes a token that is valid for 1 hour. Accepts an email
    in the request body and, if the user exists, emails the reset link.
    """

    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.get(email__iexact=email)

        send_password_reset_email.delay(user.id)

        return Response(
            {"message": _("Password reset link sent.")},
            status=status.HTTP_200_OK,
        )


@api_users_tag()
class CustomPasswordResetConfirmView(GenericAPIView):
    """Handles the reset password confirmation process."""

    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        new_password = serializer.validated_data["new_password1"]
        user.set_password(new_password)
        user.save()

        return Response(
            {"message": _("Password has been reset successfully.")},
            status=status.HTTP_200_OK,
        )

