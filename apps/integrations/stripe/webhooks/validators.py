import logging

from apps.integrations.stripe.webhooks.exceptions import InvalidStripeEventError

logger = logging.getLogger("aerobox")


def require_event_object(event: dict) -> dict:
    data = event.get("data") or {}
    obj = data.get("object")
    if not isinstance(obj, dict):
        logger.critical("Missing data.object in Stripe event", extra={"event": event})
        raise InvalidStripeEventError("Missing data.object in Stripe event.")
    return obj


def require_object_id(obj: dict, what: str) -> str:
    obj_id = obj.get("id")
    if not obj_id:
        logger.critical("Missing %s id in Stripe event object", what, extra={"object": obj})
        raise InvalidStripeEventError(f"Missing {what} id in Stripe event object.")
    return obj_id
