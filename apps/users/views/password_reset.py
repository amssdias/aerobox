from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import EmailValidator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from django.contrib.auth.password_validation import validate_password, ValidationError



class CustomPasswordResetView(APIView):
    """Sends a password reset link via email."""

    def post(self, request):
        email = request.data.get("email", "").strip()

        validation_error = self.validate_email(email)
        if validation_error:
            return Response(
                {"error": validation_error["error"]}, status=validation_error["status"]
            )

        try:
            user = User.objects.get(email__iexact=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = reverse(
                "users:password_reset_confirm", kwargs={"uidb64": uid, "token": token}
            )

            send_mail(
                "Password Reset Request",
                f"Use this link to reset your password: {reset_link}",
                "noreply@example.com",
                [user.email],
                fail_silently=False,
            )
            return Response(
                {"message": _("Password reset link sent.")}, status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"error": _("User with this email does not exist.")},
                status=status.HTTP_404_NOT_FOUND,
            )

    @staticmethod
    def validate_email(email):
        if not email:
            return {
                "error": "Email is required.",
                "status": status.HTTP_400_BAD_REQUEST,
            }

        try:
            EmailValidator()(email)
        except ValidationError:
            return {
                "error": "Invalid email format.",
                "status": status.HTTP_400_BAD_REQUEST,
            }

        return None


class CustomPasswordResetConfirmView(APIView):
    """Handles the reset password confirmation process."""

    def post(self, request, uidb64, token):
        new_password1 = request.data.get("new_password1", "").strip()
        new_password2 = request.data.get("new_password2", "").strip()

        password_validation_error = self.validate_passwords(new_password1, new_password2)
        if password_validation_error:
            return Response({"error": password_validation_error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                user.set_password(new_password1)
                user.save()
                return Response(
                    {"message": _("Password has been reset.")},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
                )
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": _("Invalid user or token.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def validate_passwords(password1, password2):
        if not password1 or not password2:
            return _("Both passwords are required.")
        if password1 != password2:
            return _("Passwords do not match.")

        try:
            validate_password(password1)
        except ValidationError as e:
            return ",".join(e.messages)

        return None