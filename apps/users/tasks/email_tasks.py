import logging
from urllib.parse import urlencode

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

logger = logging.getLogger("aerobox")
User = get_user_model()


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

        frontend_domain = settings.FRONTEND_DOMAIN
        reset_password_path = "/reset-password"
        query_params = urlencode({"uidb64": uid, "token": token})
        full_reset_link = f"{frontend_domain}{reset_password_path}?{query_params}"

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
        logger.info(f"Password reset email sent to {user.email}.")
        return True
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id} does not exist.")
        return None
    except Exception as e:
        logger.error("Failed to send email.", exc_info=True, extra={"email": user.email})
        return None
