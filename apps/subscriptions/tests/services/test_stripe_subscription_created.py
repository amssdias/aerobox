from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices, SubscriptionBillingCycleChoices
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.stripe_events.stripe_subscription_created import SubscriptionCreateddHandler
from apps.users.factories.user_factory import UserFactory


class SubscriptionCreateddHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")
        cls.plan = PlanFactory(name="Test Plan", stripe_price_id="price_test")

    def setUp(self):
        self.data = {
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer" : "cus_test",
                    "status": "incomplete",
                    "current_period_start": 1700000000,
                    "current_period_end": 1702592000,
                    "plan": {"id": "price_test"},
                    "items": {
                        "data": [
                            {
                                "plan": {
                                    "interval": "month"
                                }
                            }
                        ]
                    }
                }
            },
        }

        self.handler = SubscriptionCreateddHandler(self.data)

    def test_get_user_success(self):
        user = self.handler.get_user(data=self.data["data"]["object"])
        self.assertEqual(user, self.user)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_user_profile_does_not_exist(self, mock_logger):
        self.data["data"]["object"]["customer"] = "cus_non_existing"
        handler = SubscriptionCreateddHandler(self.data)

        user = handler.get_user(data=self.data["data"]["object"])
        self.assertIsNone(user)
        customer_id = self.data.get("data").get("object").get("customer")
        mock_logger.assert_called_once_with("No profile found for the given Stripe customer ID.", extra={"stripe_id": customer_id})

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_user_with_missing_customer_id(self, mock_logger):
        self.handler.data.pop("customer", None)

        user = self.handler.get_user(data=self.data["data"]["object"])
        self.assertIsNone(user)

        mock_logger.assert_called_once_with("Missing 'customer' key in Stripe event data.",
                                            extra={"stripe_data": self.handler.data})

    def test_get_plan_success(self):
        plan = self.handler.get_plan()
        self.assertEqual(plan, self.plan)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_plan_does_not_exist(self, mock_logger):
        self.data["data"]["object"]["plan"]["id"] = "price_non_existing"
        handler = SubscriptionCreateddHandler(self.data)

        plan = handler.get_plan()
        self.assertIsNone(plan)

        plan_id = self.data.get("data").get("object").get("plan").get("id")
        mock_logger.assert_called_once_with("No plan found for the given Stripe price ID.", extra={"stripe_price_id": plan_id})

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_plan_with_missing_plan_id(self, mock_logger):
        self.handler.data["plan"].pop("id", None)
        plan = self.handler.get_plan()
        self.assertIsNone(plan)
        mock_logger.assert_called_once_with("Missing 'id' key under 'plan' in Stripe event data.", extra={"stripe_data": self.handler.data})

    def test_create_subscription_success(self):
        subscription_id = self.data.get("data").get("object").get("id")
        self.assertFalse(Subscription.objects.filter(stripe_subscription_id=subscription_id).exists())

        self.handler.create_subscription()

        self.assertTrue(Subscription.objects.filter(stripe_subscription_id=subscription_id).exists())

    def test_create_subscription_user_none(self):
        self.handler.get_user = MagicMock(return_value=None)

        with patch("apps.subscriptions.models.Subscription.objects.get_or_create") as mock_get_or_create:
            self.handler.create_subscription()
            mock_get_or_create.assert_not_called()

    def test_create_subscription_plan_none(self):
        self.handler.get_plan = MagicMock(return_value=None)

        with patch("apps.subscriptions.models.Subscription.objects.get_or_create") as mock_get_or_create:
            self.handler.create_subscription()
            mock_get_or_create.assert_not_called()

    def test_get_subscription_status_active(self):
        self.handler.data["status"] = "active"
        status = self.handler.get_subscription_status()
        self.assertEqual(status, SubscriptionStatusChoices.ACTIVE.value)

    def test_get_subscription_status_incomplete(self):
        self.handler.data["status"] = "incomplete"
        status = self.handler.get_subscription_status()
        self.assertEqual(status, SubscriptionStatusChoices.INACTIVE.value)

    def test_get_subscription_status_unknown(self):
        self.handler.data["status"] = "unknown_status"
        status = self.handler.get_subscription_status()
        self.assertIsNone(status)

    def test_get_billing_cycle_valid(self):
        self.handler.data["items"]["data"][0]["plan"]["interval"] = "month"
        billing_cycle = self.handler.get_billing_cycle()
        self.assertEqual(billing_cycle, SubscriptionBillingCycleChoices("month").value)

    def test_get_billing_cycle_invalid(self):
        self.handler.data["items"]["data"][0]["plan"]["interval"] = "invalid_cycle"
        billing_cycle = self.handler.get_billing_cycle()
        self.assertIsNone(billing_cycle)

    @patch("apps.subscriptions.models.Subscription.objects.get_or_create")
    def test_create_subscription_existing_subscription(self, mock_get_or_create):
        mock_get_or_create.return_value = (MagicMock(), False)

        created = self.handler.create_subscription()

        mock_get_or_create.assert_called_once()
        self.assertFalse(created)

    @patch("stripe.Webhook.construct_event")
    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.SubscriptionCreateddHandler.process")
    def test_webhook_subscription_created_success(self, mock_process, mock_construct_event):
        mock_construct_event.return_value = {"type": "customer.subscription.created", "data": {"object": self.data}}
        mock_process.return_value = None

        response = self.client.post(
            reverse("stripe-webhook"),
            data={},
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature"
        )

        self.assertEqual(response.status_code, 200)
        mock_construct_event.assert_called_once()
        mock_process.assert_called_once()
