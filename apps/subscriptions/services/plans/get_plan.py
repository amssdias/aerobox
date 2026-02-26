import logging

from apps.subscriptions.models import Plan

logger = logging.getLogger("aerobox")


def get_plan(plan_stripe_price_id):
    try:
        return Plan.objects.get(stripe_price_id=plan_stripe_price_id, is_free=False)

    except Plan.DoesNotExist:
        logger.error(
            "No plan found for the given Stripe price ID.",
            extra={"stripe_price_id": plan_stripe_price_id},
        )
    except Plan.MultipleObjectsReturned:
        logger.error(
            "Multiple plans found with the same Stripe price ID. Expected only one.",
            extra={"stripe_price_id": plan_stripe_price_id},
        )

    return None
