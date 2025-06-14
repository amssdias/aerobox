from datetime import datetime
from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.constants.stripe_subscription_status import (
    INCOMPLETE,
    ACTIVE,
    PAST_DUE,
)
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.stripe_events.stripe_subscription_updated import (
    SubscriptionUpdateddHandler,
)
from apps.users.factories.user_factory import UserFactory


class SubscriptionUpdatedHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")
        cls.plan = PlanFactory(stripe_price_id="price_test")
        cls.subscription = SubscriptionFactory(
            user=cls.user,
            plan=cls.plan,
            start_date=datetime.utcnow().date(),
            end_date=datetime.utcnow().date(),
        )

    def setUp(self):
        self.data = {
            "id": self.subscription.stripe_subscription_id,
            "status": "incomplete",
        }
        self.handler = SubscriptionUpdateddHandler({"data": {"object": self.data}})

    @patch("stripe.Subscription.retrieve")
    def test_process_success(self, subscription_mock):
        subscription_mock.return_value = MagicMock(**self.data)

        self.handler.process()
        self.subscription.refresh_from_db()

        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.INACTIVE.value
        )

    @patch("stripe.Subscription.retrieve")
    def test_process_creates_subscription_when_none_exists(self, subscription_mock):
        user = UserFactory(username="testuser_1234", stripe_customer_id="cust_test1234562345")
        n_subscriptions = Subscription.objects.filter(user=user).count()

        self.handler.data["id"] = "sub_nonexist"
        data = {
            "id": "sub_nonexist",
            "customer": user.profile.stripe_customer_id,
            "status": "active",
            "plan": {"id": self.plan.stripe_price_id},
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

        subscription_mock.return_value = MagicMock(**data)
        subscription_mock.return_value.get.return_value = data.get("items")
        self.handler.process()

        self.assertEqual(Subscription.objects.filter(user=user).count(), n_subscriptions + 1)

    def test_get_subscription_status_active(self):
        status = self.handler.get_subscription_status(ACTIVE)
        self.assertEqual(status, SubscriptionStatusChoices.ACTIVE.value)

    def test_get_subscription_status_incomplete(self):
        status = self.handler.get_subscription_status(INCOMPLETE)
        self.assertEqual(status, SubscriptionStatusChoices.INACTIVE.value)

    def test_get_subscription_status_past_due(self):
        status = self.handler.get_subscription_status(PAST_DUE)
        self.assertEqual(status, SubscriptionStatusChoices.INACTIVE.value)

    def test_get_subscription_status_invalid(self):
        status = self.handler.get_subscription_status("unknown_status")
        self.assertIsNone(status)

    def test_get_subscription_not_status(self):
        status = self.handler.get_subscription_status(None)
        self.assertIsNone(status)

    def test_get_subscription_success(self):
        subscription = self.handler.get_subscription(self.subscription.stripe_subscription_id)
        self.assertEqual(subscription.id, self.subscription.id)

    @patch("config.services.stripe_services.stripe_events.subscription_mixin.logger.warning")
    def test_get_subscription_not_found(self, mock_logger):
        subscription = self.handler.get_subscription("non_existent_sub")
        self.assertIsNone(subscription)
        mock_logger.assert_called_once_with(
            "Subscription not found: The provided Stripe subscription ID does not exist.",
            extra={"stripe_subscription_id": "non_existent_sub"},
        )
