import stripe
from django.conf import settings

from apps.payments.choices.payment_choices import PaymentMethodChoices

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_checkout_session(plan, stripe_customer_id):
    success_url = f"{settings.FRONTEND_DOMAIN}/success"
    cancel_url = f"{settings.FRONTEND_DOMAIN}/cancel"

    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        payment_method_types=PaymentMethodChoices.values,
        line_items=[{
            "price": plan.stripe_price_id,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
    )

    return session.url


def get_payment_intent(payment_intent_id):
    return stripe.PaymentIntent.retrieve(payment_intent_id)

def get_payment_method(payment_method_id):
    return stripe.PaymentMethod.retrieve(payment_method_id)
