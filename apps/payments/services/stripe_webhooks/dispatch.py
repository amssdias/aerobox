import logging

from apps.payments.services.stripe_webhooks.handlers.invoice import (
    handle_invoice_paid,
    handle_invoice_created,
    handle_invoice_payment_failed,
)
from apps.subscriptions.services.stripe_webhooks.handlers.subscription import (
    handle_subscription_created,
    handle_subscription_deleted,
    handle_subscription_updated,
)

logger = logging.getLogger(__name__)

HANDLERS = {
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.created": handle_invoice_created,
    "invoice.paid": handle_invoice_paid,
    "invoice.payment_failed": handle_invoice_payment_failed,
}


def dispatch_stripe_event(event: dict) -> None:
    """
    Routes a Stripe event to the correct handler.

    Called from the webhook view after signature verification.
    """

    event_type = get_event_type(event)

    validate_event_data_object(event)

    handler = HANDLERS.get(event_type)
    if not handler:
        logger.info("Unhandled Stripe event type: %s", event_type)
        return

    handler(event)


def get_event_type(event):
    event_type = event.get("type")
    if not event_type:
        logger.error(
            "Webhook event missing required 'type' field.", extra={"event": event}
        )
        raise KeyError("Missing required event type in webhook event.")
    return event_type


def validate_event_data_object(event):
    event_data = get_event_data(event)
    get_event_data_object(event_data, event)


def get_event_data(event):
    event_data = event.get("data")
    if not event_data or not isinstance(event_data, dict):
        logger.error(
            "Webhook event missing required 'data' field.", extra={"event": event}
        )
        raise KeyError("Missing required 'data' field in webhook event.")
    return event_data


def get_event_data_object(event_data, event):
    event_object = event_data.get("object")
    if not event_object:
        logger.error(
            "Webhook event missing required 'data.object' field.",
            extra={"event": event},
        )
        raise KeyError("Missing required 'data.object' field in webhook event.")
    return event_object
