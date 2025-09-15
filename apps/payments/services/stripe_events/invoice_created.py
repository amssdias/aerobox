import logging

from django.db import transaction, IntegrityError

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.models import Payment
from apps.subscriptions.services.stripe_events.stripe_subscription_created import SubscriptionCreateddHandler
from config.services.stripe_services.stripe_events.base_event import StripeEventHandler
from config.services.stripe_services.stripe_events.invoice_event_mixin import StripeInvoiceMixin
from config.services.stripe_services.stripe_events.subscription_mixin import StripeSubscriptionMixin

logger = logging.getLogger("aerobox")


class InvoiceCreatedHandler(
    StripeEventHandler,
    StripeInvoiceMixin,
    StripeSubscriptionMixin,
):
    """
    Handles the `invoice.created` event.
    """

    def process(self):
        self.handle_payment_creation()

    def handle_payment_creation(self):
        sripe_invoice_id = self.get_invoice_id()
        stripe_invoice = self.get_stripe_invoice(stripe_invoice_id=sripe_invoice_id)

        subscription = self.get_or_create_subscription(
            stripe_subscription_id=self.get_subscription_id_from_invoice(stripe_invoice)
        )
        user = subscription.user if subscription else None
        hosted_invoice_url = stripe_invoice.hosted_invoice_url
        invoice_pdf_url = stripe_invoice.invoice_pdf
        amount = self.convert_cents_to_euros(stripe_invoice.amount_paid or stripe_invoice.amount_due)

        if not self.is_valid_payment(user, subscription, sripe_invoice_id, amount):
            return

        return self.create_payment(
            user=user,
            subscription=subscription,
            status=PaymentStatusChoices.PENDING.value,
            stripe_invoice_id=sripe_invoice_id,
            invoice_url=hosted_invoice_url,
            invoice_pdf_url=invoice_pdf_url,
            amount=amount,
        )

    @staticmethod
    def get_subscription_id_from_invoice(stripe_invoice):
        return stripe_invoice.parent.get("subscription_details", {}).get("subscription")

    def get_or_create_subscription(self, stripe_subscription_id):
        subscription = self.get_subscription(stripe_subscription_id)
        return subscription or SubscriptionCreateddHandler(event=self.event).create_subscription(stripe_subscription_id)

    def is_valid_payment(self, user, subscription, stripe_invoice_id, amount_due):
        missing_fields = []
        if not user:
            missing_fields.append("user")
        if not subscription:
            missing_fields.append("subscription")
        if amount_due is None:
            missing_fields.append("amount_due")

        if missing_fields:
            logger.critical(
                f"Failed to create payment instance for invoice {stripe_invoice_id}. "
                f"Missing required fields: {', '.join(missing_fields)}. "
                "Check if the Stripe event contains valid customer and subscription data.",
                extra={"stripe_data": self.data},
            )
            raise RuntimeError(f"Payment data is incomplete for Invoice ID: {stripe_invoice_id}. Stripe should retry.")

        return True

    @staticmethod
    def create_payment(user, subscription, status, stripe_invoice_id, invoice_url, invoice_pdf_url, amount):

        try:
            with transaction.atomic():
                payment, created = Payment.objects.get_or_create(
                    stripe_invoice_id=stripe_invoice_id,
                    defaults={
                        "user": user,
                        "subscription": subscription,
                        "status": status,
                        "invoice_url": invoice_url,
                        "invoice_pdf_url": invoice_pdf_url,
                        "amount": amount,
                    }
                )
                logger.info(f"Payment created successfully for invoice {stripe_invoice_id}.")

        except IntegrityError:
            payment = Payment.objects.get(stripe_invoice_id=stripe_invoice_id)

        return payment
