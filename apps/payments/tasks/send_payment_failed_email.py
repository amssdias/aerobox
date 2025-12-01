import logging
from datetime import timedelta
from typing import Optional

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.translation import override, gettext as _

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices

logger = logging.getLogger("aerobox")
User = get_user_model()


@shared_task
def send_invoice_payment_failed_email(user_id: str) -> Optional[bool]:
    try:
        user = User.objects.get(id=user_id)

        with override(user.profile.language):

            # Render the email content
            subject = _("Payment Failed – Update Your Payment Method")
            to_email = [user.email]

            subscription = user.subscriptions.filter(status=SubscriptionStatusChoices.PAST_DUE.value).first()
            if not subscription:
                logger.info(f"No active subscription found for user {user.email}. Email not sent.")
                return

            deadline = subscription.end_date + timedelta(days=7)
            context = {
                "user": user,
                "attempts": 2,
                "deadline_date": format_html("<strong>{}</strong>", deadline.strftime("%d/%m/%Y"))
            }

            # Plain-text version
            text_content = _("Payment Failed – Update Your Payment Method")

            # HTML version
            html_content = render_to_string("emails/email_payment_failed.html", context)

            # Send the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                to=to_email,
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            logger.info(f"Failed payment email sent to: {user.email}.")
            return True
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id} does not exist. Email payment failed not sent.")
        return None
    except Exception as e:
        logger.error(
            "Failed to send payment failed email.",
            exc_info=True,
            extra={"email": user.email},
        )
        return None
