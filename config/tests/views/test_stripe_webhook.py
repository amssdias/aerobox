from unittest.mock import patch

import stripe
from django.test import TestCase
from django.urls import reverse


class SubscriptionCreatedHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("stripe-webhook")
        cls.data = {"data": {"objects": {}}}

    @patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError(
            "message", "invalid_signature"
        ),
    )
    def test_webhook_subscription_created_invalid_signature(self, mock_construct_event):
        response = self.client.post(
            self.url,
            data=self.data,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid_signature",
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content.decode(),
            {"error": "Invalid Stripe signature. Request could not be verified."},
        )
        mock_construct_event.assert_called_once()

    @patch("stripe.Webhook.construct_event", side_effect=Exception("Webhook error"))
    def test_webhook_subscription_created_general_error(self, mock_construct_event):
        response = self.client.post(
            self.url,
            data=self.data,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content.decode(),
            {"error": "Unexpected error while processing the Stripe webhook."},
        )
        mock_construct_event.assert_called_once()
