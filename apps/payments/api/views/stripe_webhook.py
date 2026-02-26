from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.integrations.stripe.client import stripe
from apps.payments.services.stripe_webhooks.dispatch import dispatch_stripe_event


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    """
    Handles Stripe webhooks for events like successful checkout session completions.
    """

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.headers.get("Stripe-Signature")

        try:
            # Verify that the webhooks is from Stripe
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            return JsonResponse({"error": "Invalid Stripe signature. Request could not be verified."}, status=400)
        except Exception:
            return JsonResponse({"error": "Unexpected error while processing the Stripe webhook."}, status=400)

        dispatch_stripe_event(event)

        return JsonResponse({"status": "success"})
