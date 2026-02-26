from datetime import datetime, time, timezone, timedelta
from unittest.mock import patch, sentinel, Mock

from django.test import TestCase

from apps.subscriptions.factories.plan_factory import PlanProFactory
from apps.subscriptions.factories.subscription import SubscriptionProPlanFactory
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.subscriptions.ensure_subscription import (
    get_or_sync_subscription_from_stripe,
    create_subscription_from_stripe,
)


class EnsureSubscriptionServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan_pro = PlanProFactory()
        cls.stripe_subscription_id = "sub_test_123"
        cls.subscription = SubscriptionProPlanFactory(
            stripe_subscription_id=cls.stripe_subscription_id,
        )

    def make_stripe_subscription_mock_for_summary(
            self,
            subscription_id="sub_test_123",
            customer_id="cus_test_123",
            plan_id="price_test_123",
            billing_cycle_start=None,
            billing_cycle_end=None,
            interval="month",
            cancel_at_period_end=False,
            ended_at=None,
    ):
        """
        Builds a Stripe "subscription" mock that works with:
          - stripe_subscription.get("id"), .get("customer")
          - stripe_subscription.plan.get("id")
          - get_subscription_billing_cycle_start/end that read:
              stripe_subscription.get("items", {}).get("data", [{}])[0].get("current_period_start"/"current_period_end")
          - stripe_subscription.cancel_at_period_end
          - stripe_subscription.ended_at
        """
        stripe_subscription = Mock(name="StripeSubscription")
        billing_cycle_start = billing_cycle_start or datetime.now().date()
        billing_cycle_end = billing_cycle_end or datetime.now().date() + timedelta(days=30)

        items_payload = {
            "items": {
                "data": [
                    {
                        "current_period_start": self.billing_cycle_date_to_epoch_seconds(billing_cycle_start),
                        "current_period_end": self.billing_cycle_date_to_epoch_seconds(billing_cycle_end),
                        "plan": {"interval": interval},
                    }
                ]
            }
        }

        def _get(key, default=None):
            base = {
                "id": subscription_id,
                "customer": customer_id,
                **items_payload,
            }
            return base.get(key, default)

        stripe_subscription.get.side_effect = _get

        stripe_subscription.plan = {"id": plan_id}
        stripe_subscription.cancel_at_period_end = cancel_at_period_end
        stripe_subscription.ended_at = ended_at

        return stripe_subscription

    @staticmethod
    def billing_cycle_date_to_epoch_seconds(d) -> int:
        if isinstance(d, datetime):
            dt = d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
        else:
            dt = datetime.combine(d, time(0, 0, 0), tzinfo=timezone.utc)
        return int(dt.timestamp())

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription_from_stripe")
    def test_get_or_sync_returns_existing_subscription_and_does_not_call_create(self, create_from_stripe_mock):
        result = get_or_sync_subscription_from_stripe(self.stripe_subscription_id)

        self.assertEqual(result, self.subscription)
        create_from_stripe_mock.assert_not_called()

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription_from_stripe")
    def test_get_or_sync_calls_create_from_stripe_when_missing(self, create_from_stripe_mock):
        create_from_stripe_mock.return_value = sentinel.created_sub

        result = get_or_sync_subscription_from_stripe("None")

        self.assertEqual(result, sentinel.created_sub)
        create_from_stripe_mock.assert_called_once_with("None")

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription_from_stripe")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_subscription")
    def _test_get_or_sync_propagates_exception_from_create(
            self, get_subscription_mock, create_from_stripe_mock
    ):
        get_subscription_mock.return_value = None
        create_from_stripe_mock.side_effect = RuntimeError("stripe exploded")

        with self.assertRaises(RuntimeError):
            get_or_sync_subscription_from_stripe(self.stripe_subscription_id)

    # -------------------------
    # create_subscription_from_stripe
    # -------------------------

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_stripe_subscription")
    def test_create_from_stripe_happy_path_calls_stripe_mapper_and_create(self, get_stripe_sub_mock):
        stripe_sub = self.make_stripe_subscription_mock_for_summary(
            subscription_id=self.subscription.id,
            customer_id=self.subscription.user.profile.stripe_customer_id,
            plan_id=self.plan_pro.stripe_price_id,
            cancel_at_period_end=True,
            ended_at=None,
        )

        get_stripe_sub_mock.return_value = stripe_sub

        subscription = create_subscription_from_stripe(self.stripe_subscription_id)

        self.assertTrue(subscription)
        self.assertIsInstance(subscription, Subscription)
        get_stripe_sub_mock.assert_called_once_with(self.stripe_subscription_id)

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.to_subscription_summary")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_stripe_subscription")
    def test_create_from_stripe_propagates_exception_from_stripe(
            self, get_stripe_sub_mock, to_summary_mock, create_sub_mock
    ):
        get_stripe_sub_mock.side_effect = Exception("Stripe API error")

        with self.assertRaises(Exception):
            create_subscription_from_stripe(self.stripe_subscription_id)

        to_summary_mock.assert_not_called()
        create_sub_mock.assert_not_called()

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.to_subscription_summary")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_stripe_subscription")
    def test_create_from_stripe_propagates_exception_from_mapper(
            self, get_stripe_sub_mock, to_summary_mock, create_sub_mock
    ):
        get_stripe_sub_mock.return_value = sentinel.stripe_sub
        to_summary_mock.side_effect = ValueError("bad stripe payload")

        with self.assertRaises(ValueError):
            create_subscription_from_stripe(self.stripe_subscription_id)

        create_sub_mock.assert_not_called()

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.to_subscription_summary")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_stripe_subscription")
    def test_create_from_stripe_propagates_exception_from_create_subscription(
            self, get_stripe_sub_mock, to_summary_mock, create_sub_mock
    ):
        get_stripe_sub_mock.return_value = sentinel.stripe_sub
        to_summary_mock.return_value = sentinel.summary
        create_sub_mock.side_effect = RuntimeError("db error")

        with self.assertRaises(RuntimeError):
            create_subscription_from_stripe(self.stripe_subscription_id)

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.create_subscription")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.to_subscription_summary")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_stripe_subscription")
    def test_create_from_stripe_does_not_mutate_summary_object(
            self, get_stripe_sub_mock, to_summary_mock, create_sub_mock
    ):
        summary_obj = object()
        get_stripe_sub_mock.return_value = sentinel.stripe_sub
        to_summary_mock.return_value = summary_obj
        create_sub_mock.return_value = sentinel.created

        create_subscription_from_stripe(self.stripe_subscription_id)

        create_sub_mock.assert_called_once_with(summary_obj)

    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.get_stripe_subscription")
    @patch("apps.subscriptions.services.subscriptions.ensure_subscription.logger.exception")
    def test_create_subscription_from_stripe_logs_exception_with_traceback_when_stripe_fails(
            self, logger_mock, get_stripe_subscription_mock
    ):
        stripe_subscription_id = "sub_boom_123"
        get_stripe_subscription_mock.side_effect = RuntimeError("Stripe is down")

        with self.assertRaises(RuntimeError):
            create_subscription_from_stripe(stripe_subscription_id)

            logger_mock.exception.assert_called_once()
            logger_mock.assert_called_once_with("Subscription not created from stripe.")
