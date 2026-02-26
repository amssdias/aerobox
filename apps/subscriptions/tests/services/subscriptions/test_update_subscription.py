from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionProPlanFactory
from apps.subscriptions.services.subscriptions.update_subscription import update_subscription
from apps.users.factories.user_factory import UserFactory


class UpdateSubscriptionServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.today = datetime.now().date()
        cls.ended_at = cls.today + timedelta(days=7)

        cls.subscription = SubscriptionProPlanFactory(user=cls.user, stripe_subscription_id="sub_1234")

    @patch("apps.subscriptions.services.subscriptions.update_subscription.get_subscription")
    @patch("apps.subscriptions.services.subscriptions.update_subscription.update_cancel_subscription_status")
    def test_update_subscription_when_cancel_at_period_end_false_does_not_call_anything_and_returns_true(self,
                                                                                                         get_sub_mock,
                                                                                                         cancel_mock):
        summary = SimpleNamespace(
            cancel_at_period_end=False,
            subcription_id=str(self.subscription.stripe_subscription_id),
            ended_at=self.ended_at,
        )

        result = update_subscription(summary)

        self.assertTrue(result)
        get_sub_mock.assert_not_called()
        cancel_mock.assert_not_called()

    @patch("apps.subscriptions.services.subscriptions.update_subscription.get_subscription")
    @patch("apps.subscriptions.services.subscriptions.update_subscription.update_cancel_subscription_status")
    def test_update_subscription_when_cancel_at_period_end_true_calls_get_subscription(self, get_sub_mock, cancel_mock):
        summary = SimpleNamespace(
            cancel_at_period_end=True,
            subcription_id=str(self.subscription.stripe_subscription_id),
            ended_at=self.ended_at,
        )

        get_sub_mock.return_value = self.subscription

        update_subscription(summary)

        get_sub_mock.assert_called_once()
        cancel_mock.assert_called_once()

    def test_update_subscription_integration_cancels_subscription_in_db_when_cancel_at_period_end_true(self):
        summary = SimpleNamespace(
            cancel_at_period_end=True,
            subcription_id=str(self.subscription.stripe_subscription_id),
            ended_at=self.ended_at,
        )

        update_subscription(summary)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, SubscriptionStatusChoices.CANCELED.value)
        self.assertEqual(self.subscription.end_date, self.ended_at)

    def _test_update_subscription_propagates_exception_from_get_subscription(self):
        summary = SimpleNamespace(
            cancel_at_period_end=True,
            subcription_id="does-not-matter",
            ended_at=self.ended_at,
        )

        with patch(
                "apps.subscriptions.services.subscriptions.update_subscription.get_subscription",
                side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                update_subscription(summary)
