from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from apps.users.serializers.password_reset_serializer import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
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

        self.send_password_reset_email(user)

        return Response(
            {"message": _("Password reset link sent.")},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def send_password_reset_email(user):
        """Generates a password reset link and sends it to the user's email."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uid, "token": token}
        )
        frontend_domain = settings.FRONTEND_DOMAIN
        full_reset_link = f"{frontend_domain}{reset_link}"

        send_mail(
            _("Password Reset Request"),
            _("Use this link to reset your password: {link}").format(
                link=full_reset_link
            ),
            "noreply@example.com",
            [user.email],
            fail_silently=False,
        )


@api_users_tag()
class CustomPasswordResetConfirmView(GenericAPIView):
    """Handles the reset password confirmation process."""

    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, uidb64, token):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                user.set_password(serializer.validated_data["new_password1"])
                user.save()
                return Response(
                    {"message": _("Password has been reset.")},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": _("Invalid token.")}, status=status.HTTP_400_BAD_REQUEST
                )
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": _("Invalid user or token.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
