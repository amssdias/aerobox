from datetime import datetime
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices, SubscriptionBillingCycleChoices
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory
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
                    "plan": {"id": "price_test"},
                    "items": {
                        "data": [
                            {
                                "current_period_start": 1700000000,
                                "current_period_end": 1702592000,
                                "plan": {
                                    "interval": "month"
                                }
                            }
                        ]
                    }
                }
            },
        }
        self.subscription_mock = MagicMock(**self.data["data"]["object"])
        self.subscription_mock.get.return_value = self.data["data"]["object"]["items"]
        self.handler = SubscriptionCreateddHandler(self.data)

    def test_get_user_success(self):
        user = self.handler.get_user(stripe_customer_id=self.user.profile.stripe_customer_id)
        self.assertEqual(user, self.user)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_user_profile_does_not_exist(self, mock_logger):
        user = self.handler.get_user(stripe_customer_id="cus_non_existing")

        self.assertIsNone(user)
        mock_logger.assert_called_once_with("No profile found for the given Stripe customer ID.",
                                            extra={"stripe_customer_id": "cus_non_existing"})

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_user_with_missing_customer_id(self, mock_logger):
        user = self.handler.get_user(stripe_customer_id=None)

        self.assertIsNone(user)
        mock_logger.assert_called_once_with("No profile found for the given Stripe customer ID.",
                                            extra={"stripe_customer_id": None})

    def test_get_plan_success(self):
        plan = self.handler.get_plan(plan_stripe_price_id=self.subscription_mock.plan.get("id"))
        self.assertEqual(plan, self.plan)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_plan_does_not_exist(self, mock_logger):
        plan = self.handler.get_plan(plan_stripe_price_id="price_non_existing")

        self.assertIsNone(plan)
        mock_logger.assert_called_once_with("No plan found for the given Stripe price ID.",
                                            extra={"stripe_price_id": "price_non_existing"})

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_created.logger.error")
    def test_get_plan_with_missing_plan_id(self, mock_logger):
        plan = self.handler.get_plan(plan_stripe_price_id=None)

        self.assertIsNone(plan)
        mock_logger.assert_called_once_with(
            "No plan found for the given Stripe price ID.", extra={"stripe_price_id": None}
        )

    @patch("stripe.Subscription.retrieve")
    def test_create_subscription_success(self, subscription_mock):
        subscription_id = self.subscription_mock.id
        self.assertFalse(Subscription.objects.filter(stripe_subscription_id=subscription_id).exists())

        subscription_mock.return_value = self.subscription_mock
        subscription = self.handler.create_subscription()

        self.assertTrue(subscription)
        items = self.data["data"]["object"]["items"]
        start_date = datetime.utcfromtimestamp(items["data"][0]["current_period_start"]).date()
        end_date = datetime.utcfromtimestamp(items["data"][0]["current_period_end"]).date()

        self.assertTrue(Subscription.objects.filter(stripe_subscription_id=subscription_id).exists())
        self.assertEqual(subscription.plan.id, self.plan.id)
        self.assertEqual(subscription.status, SubscriptionStatusChoices.INACTIVE)
        self.assertEqual(subscription.billing_cycle, SubscriptionBillingCycleChoices.MONTH)
        self.assertEqual(subscription.start_date, start_date)
        self.assertEqual(subscription.end_date, end_date)
        self.assertTrue(subscription.is_recurring)

    @patch("stripe.Subscription.retrieve")
    def test_create_subscription_user_none(self, subscription_mock):
        self.handler.get_user = MagicMock(return_value=None)

        with patch("apps.subscriptions.models.Subscription.objects.get_or_create") as mock_get_or_create:
            self.handler.create_subscription()
            mock_get_or_create.assert_not_called()

    @patch("stripe.Subscription.retrieve")
    def test_create_subscription_plan_none(self, subscription_mock):
        self.handler.get_plan = MagicMock(return_value=None)

        with patch("apps.subscriptions.models.Subscription.objects.get_or_create") as mock_get_or_create:
            self.handler.create_subscription()
            mock_get_or_create.assert_not_called()

    def test_get_subscription_status_active(self):
        status = self.handler.get_subscription_status(status="active")
        self.assertEqual(status, SubscriptionStatusChoices.ACTIVE.value)

    def test_get_subscription_status_incomplete(self):
        status = self.handler.get_subscription_status(status="incomplete")
        self.assertEqual(status, SubscriptionStatusChoices.INACTIVE.value)

    def test_get_subscription_status_unknown(self):
        status = self.handler.get_subscription_status(status="unknown_status")
        self.assertIsNone(status)

    def test_get_billing_cycle_valid(self):
        billing_cycle = self.handler.get_subscription_billing_cycle_interval(
            stripe_subscription={
                "items": {
                    "data": [{"plan": {"interval": "month"}}]
                }
            }
        )
        self.assertEqual(billing_cycle, SubscriptionBillingCycleChoices("month").value)

    def test_get_billing_cycle_invalid(self):
        billing_cycle = self.handler.get_subscription_billing_cycle_interval(stripe_subscription={})
        self.assertIsNone(billing_cycle)

    @patch("stripe.Subscription.retrieve")
    def test_create_subscription_existing_subscription(self, subscription_mock):
        SubscriptionFactory(stripe_subscription_id="sub_123", user=self.user, plan=self.plan)
        n_subscriptions = Subscription.objects.all().count()
        subscription_mock.return_value = self.subscription_mock
        self.handler.create_subscription()

        self.assertEqual(Subscription.objects.all().count(), n_subscriptions)

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
