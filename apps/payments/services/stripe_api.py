import stripe
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.integrations.stripe.payments.checkout_session import get_stripe_session
from apps.integrations.stripe.payments.dto.checkout_session import CheckoutSessionInfo
from apps.integrations.stripe.payments.mappers.checkout_session import to_checkout_session_summary
from apps.payments.choices.payment_choices import PaymentMethodChoices
from apps.payments.domain.exceptions import CheckoutSessionPermissionDeniedError

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_checkout_session(plan, stripe_customer_id):
    success_url = f"{settings.FRONTEND_DOMAIN}/payment-success"
    cancel_url = f"{settings.FRONTEND_DOMAIN}/payment-failed"

    # Move to stripe integrations app
    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        payment_method_types=PaymentMethodChoices.values,
        line_items=[{
            "price": plan.stripe_price_id,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        automatic_tax={"enabled": True},
        customer_update={"address": "auto"},
    )

    return session.url


def get_payment_method(payment_method_id):
    return stripe.PaymentMethod.retrieve(payment_method_id)


def get_stripe_session_info(session_id: str, user) -> CheckoutSessionInfo:
    session = get_stripe_session(session_id)
    customer = session.get("customer")
    user_customer_id = user.profile.stripe_customer_id
    customer_id = customer.get("id") if isinstance(customer, dict) else customer

    if not user_customer_id or not customer_id:
        raise CheckoutSessionPermissionDeniedError(
            _("Unable to validate checkout session ownership.")
        )

    if user_customer_id != customer_id:
        raise CheckoutSessionPermissionDeniedError(
            _("You do not have permission to access this checkout session.")
        )

    return to_checkout_session_summary(session)
