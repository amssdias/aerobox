import logging

from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

logger = logging.getLogger("aerobox")


@shared_task
def send_invoice_payment_success_email(user_id: str, invoice_pdf_url: str) -> None:
    try:
        user = User.objects.get(id=user_id)

        # Render the email content
        subject = _("Payment Successful — Your Invoice is Ready")
        to_email = [user.email]
        context = {"invoice_pdf_url": invoice_pdf_url, "user": user}

        # Plain-text version
        text_content = _("Use this link to see your invoice: {link}").format(
            link=invoice_pdf_url
        )

        # HTML version
        html_content = render_to_string("emails/email_invoice_paid.html", context)

        # Send the email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            to=to_email,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        logger.info(f"Invoice paid email send to: {user.email}.")
        return True
    except User.DoesNotExist:
        logger.warning(f"User with ID {user_id} does not exist.")
        return None
    except Exception as e:
        logger.error(
            "Failed to send invoice paid email.",
            exc_info=True,
            extra={"email": user.email},
        )
        return None
