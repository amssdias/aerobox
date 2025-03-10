from datetime import datetime
from unittest.mock import patch

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

    def test_process_success(self):
        self.handler.process()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.INACTIVE.value
        )

    @patch("config.services.stripe_services.stripe_events.customer_event.logger.error")
    def test_process_subscription_does_not_exist(self, mock_logger):
        subscription_id = "non_existent_sub"
        self.handler.data["id"] = subscription_id
        with self.assertRaises(ValueError) as context:
            self.handler.process()

        mock_logger.assert_called_once_with(
            "Subscription not found: The provided Stripe subscription ID does not exist.",
            extra={"stripe_subscription_id": self.data.get("id")},
        )

    def test_get_subscription_status_active(self):
        self.handler.data["status"] = ACTIVE
        status = self.handler.get_subscription_status()
        self.assertEqual(status, SubscriptionStatusChoices.ACTIVE.value)

    def test_get_subscription_status_incomplete(self):
        self.handler.data["status"] = INCOMPLETE
        status = self.handler.get_subscription_status()
        self.assertEqual(status, SubscriptionStatusChoices.INACTIVE.value)

    def test_get_subscription_status_past_due(self):
        self.handler.data["status"] = PAST_DUE
        status = self.handler.get_subscription_status()
        self.assertEqual(status, SubscriptionStatusChoices.INACTIVE.value)

    def test_get_subscription_status_invalid(self):
        self.handler.data["status"] = "unknown_status"
        status = self.handler.get_subscription_status()
        self.assertIsNone(status)

    def test_get_subscription_not_status(self):
        del self.handler.data["status"]
        status = self.handler.get_subscription_status()
        self.assertIsNone(status)

    @patch("apps.subscriptions.models.Subscription.objects.get")
    def test_get_subscription_success(self, mock_get):
        mock_get.return_value = self.subscription
        subscription = self.handler.get_subscription("sub_test")
        self.assertEqual(subscription.id, self.subscription.id)

    @patch("config.services.stripe_services.stripe_events.customer_event.logger.error")
    @patch(
        "apps.subscriptions.models.Subscription.objects.get",
        side_effect=Subscription.DoesNotExist,
    )
    def test_get_subscription_not_found(self, mock_get, mock_logger):
        subscription = self.handler.get_subscription("non_existent_sub")
        self.assertIsNone(subscription)
        mock_logger.assert_called_once_with(
            "Subscription not found: The provided Stripe subscription ID does not exist.",
            extra={"stripe_subscription_id": "non_existent_sub"},
        )
