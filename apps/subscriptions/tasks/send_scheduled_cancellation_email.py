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
def send_scheduled_cancellation_email(user_id: str) -> None:
    try:
        user = User.objects.get(id=user_id)

        with override(user.profile.language):
            sub = user.active_subscription

            if not sub:
                return

            # Render the email content
            subject = _("We’ve scheduled your subscription to cancel at the end of your billing period")
            to_email = [user.email]
            context = {
                "user_name": user.username,
                "dashboard_url": settings.FRONTEND_DOMAIN,
                "current_end_period": sub.end_date.strftime("%d/%m/%Y"),
            }

            text_content = _(
                "Hi {user_name},\n\n"
                "This is to confirm that your subscription has been scheduled to cancel at the end of your current billing period ({end_date}).\n\n"
                "Until then, you’ll continue to enjoy all the benefits of your current plan. "
                "After your subscription ends, your account will automatically switch to our Free Plan.\n\n"
                "Please note that some features will no longer be available under the Free Plan, "
                "but you can upgrade again anytime.\n\n"
                "Go to your dashboard: {dashboard_url}\n\n"
                "Thank you for trusting us.\n"
                "Best regards,\n"
                "The Aerobox Team"
            ).format(
                user_name=user.username,
                end_date=sub.end_date.strftime("%d/%m/%Y"),
                dashboard_url=settings.FRONTEND_DOMAIN,
            )

            # HTML version
            html_content = render_to_string("emails/subscription_cancellation_scheduled_email.html", context)

            # Send the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                to=to_email,
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            logger.info(f"Scheduled cancellation email send to: {user.email}.")
            return True
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id} does not exist.")
        return None
    except Exception as e:
        logger.error(
            "Failed to send scheduled cancellation email.",
            exc_info=True,
            extra={"email": user.email},
        )
        return None
