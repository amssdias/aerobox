import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import override, gettext as _

logger = logging.getLogger("aerobox")
User = get_user_model()


@shared_task
def send_subscription_cancelled_email(user_id: str) -> None:
    try:
        user = User.objects.get(id=user_id)

        with override(user.profile.language):
            # Render the email content
            subject = _("Your subscription has been cancelled — You’re now on our Free Plan")
            to_email = [user.email]
            context = {
                "user_name": user.username,
                "dashboard_url": settings.FRONTEND_DOMAIN,
            }

            text_content = _(
                "Hi {user_name},\n\n"
                "Your subscription has just been cancelled. From now on, your account is on our Free Plan.\n\n"
                "You’ll still have access to your files and account, but some premium features are no longer available. "
                "You can upgrade again at any time if you’d like to regain full access.\n\n"
                "Go to your dashboard: {dashboard_url}\n\n"
                "Thank you for being with us.\n"
                "Best regards,\n"
                "The Aerobox Team"
            ).format(
                user_name=user.username,
                dashboard_url=settings.FRONTEND_DOMAIN,
            )

            # HTML version
            html_content = render_to_string("emails/subscription_cancelled_email.html", context)

            # Send the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                to=to_email,
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            logger.info(f"Subscription cancellation email sent to: {user.email}.")
            return True
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id} does not exist.")
        return None
    except Exception as e:
        logger.error(
            "Failed to send subscription cancellation email.",
            exc_info=True,
            extra={"email": user.email},
        )
        return None
