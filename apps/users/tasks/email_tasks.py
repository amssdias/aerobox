from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _


@shared_task
def send_password_reset_email(user_id):
    """
    Task to send a password reset email to a user.
    Args:
        user_id (int): The ID of the user.
    """
    try:
        user = User.objects.get(id=user_id)

        # Generate the reset link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uid, "token": token}
        )
        frontend_domain = settings.FRONTEND_DOMAIN
        full_reset_link = f"{frontend_domain}{reset_link}"

        # Render the email content
        subject = _("Password Reset Request")
        to_email = [user.email]
        context = {"reset_link": full_reset_link, "user": user}

        # Plain-text version
        text_content = _("Use this link to reset your password: {link}").format(
            link=full_reset_link
        )

        # HTML version
        html_content = render_to_string("emails/password_reset_email.html", context)

        # Send the email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            to=to_email,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return f"Password reset email sent to {user.email}."
    except User.DoesNotExist:
        return f"User with ID {user_id} does not exist."
    except Exception as e:
        return f"Failed to send email: {e}"
