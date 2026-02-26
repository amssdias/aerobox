from datetime import date, timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from apps.integrations.stripe.subscriptions.dto.subscription import SubscriptionSummary
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.plan_factory import PlanProFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.subscriptions.create_subscription import (
    create_subscription,
)
from apps.users.factories.user_factory import UserFactory


class CreateSubscriptionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="username", email="user@example.com", stripe_customer_id="cus_123"
        )
        cls.plan_pro = PlanProFactory()

    def setUp(self) -> None:
        today = date.today()
        self.summary = SubscriptionSummary(
            subscription_id="sub_123",
            customer_id=self.user.profile.stripe_customer_id,
            plan_id=self.plan_pro.stripe_price_id,
            billing_cycle_start=today,
            billing_cycle_end=today + timedelta(days=30),
            billing_cycle_interval="month",
            cancel_at_period_end=None,
            ended_at=None,
        )

    @patch("apps.subscriptions.services.subscriptions.create_subscription.get_user")
    def test_returns_false_when_user_missing(self, mock_get_user):
        mock_get_user.return_value = None

        result = create_subscription(self.summary)

        self.assertFalse(result)
        self.assertEqual(Subscription.objects.count(), 0)

    @patch("apps.subscriptions.services.subscriptions.create_subscription.get_plan")
    def test_returns_false_when_plan_missing(self, mock_get_plan):
        mock_get_plan.return_value = None

        result = create_subscription(self.summary)

        self.assertFalse(result)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_returns_false_when_billing_dates_missing(self):
        bad = SubscriptionSummary(
            **{**self.summary.__dict__, "billing_cycle_start": None}
        )

        result = create_subscription(bad)

        self.assertFalse(result)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_creates_subscription_with_expected_defaults(self):
        subscription = create_subscription(self.summary)

        self.assertIsInstance(subscription, Subscription)
        self.assertEqual(Subscription.objects.count(), 1)

        subscription.refresh_from_db()
        self.assertEqual(
            subscription.stripe_subscription_id, self.summary.subscription_id
        )
        self.assertEqual(subscription.user_id, self.user.id)
        self.assertEqual(subscription.plan_id, self.plan_pro.id)
        self.assertEqual(
            subscription.billing_cycle, self.summary.billing_cycle_interval
        )
        self.assertEqual(subscription.start_date, self.summary.billing_cycle_start)
        self.assertEqual(subscription.end_date, self.summary.billing_cycle_end)
        self.assertEqual(subscription.status, SubscriptionStatusChoices.INACTIVE.value)
        self.assertIsNone(subscription.trial_start_date)
        self.assertTrue(subscription.is_recurring)

    @patch.object(Subscription.objects, "get")
    @patch.object(Subscription.objects, "get_or_create")
    def test_on_integrity_error_fetches_existing_subscription(
            self, mock_get_or_create, mock_get
    ):
        existing = SubscriptionFactory(
            stripe_subscription_id=self.summary.subscription_id,
            user=self.user,
            plan=self.plan_pro,
        )
        mock_get_or_create.side_effect = IntegrityError("dup key")
        mock_get.return_value = existing

        result = create_subscription(self.summary)

        self.assertIs(result, existing)
        mock_get_or_create.assert_called_once()
        mock_get.assert_called_once_with(
            stripe_subscription_id=self.summary.subscription_id
        )

    def test_returns_false_when_billing_cycle_end_missing(self):
        bad = SubscriptionSummary(
            **{**self.summary.__dict__, "billing_cycle_end": None}
        )

        result = create_subscription(bad)

        self.assertFalse(result)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_returns_false_when_billing_cycle_interval_missing(self):
        bad = SubscriptionSummary(
            **{**self.summary.__dict__, "billing_cycle_interval": None}
        )

        result = create_subscription(bad)

        self.assertFalse(result)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_when_subscription_exists_get_or_create_returns_existing(self):
        existing = SubscriptionFactory(
            stripe_subscription_id=self.summary.subscription_id,
            user=self.user,
            plan=self.plan_pro,
            billing_cycle="year",  # deliberately different to prove no overwrite
        )

        result = create_subscription(self.summary)

        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(result.id, existing.id)

    def test_existing_subscription_fields_are_not_overwritten(self):
        existing = SubscriptionFactory(
            stripe_subscription_id=self.summary.subscription_id,
            user=self.user,
            plan=self.plan_pro,
            billing_cycle="year",
            status=SubscriptionStatusChoices.ACTIVE.value,
            is_recurring=False,
        )

        result = create_subscription(self.summary)
        result.refresh_from_db()

        self.assertEqual(result.id, existing.id)
        self.assertEqual(result.billing_cycle, "year")
        self.assertEqual(result.status, SubscriptionStatusChoices.ACTIVE.value)
        self.assertFalse(result.is_recurring)

    def test_calling_twice_is_idempotent_does_not_duplicate(self):
        first = create_subscription(self.summary)
        second = create_subscription(self.summary)

        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(first.id, second.id)

    @patch.object(Subscription.objects, "get_or_create")
    def test_get_or_create_called_with_stripe_subscription_id(self, mock_get_or_create):
        fake_sub = SubscriptionFactory.build(
            stripe_subscription_id=self.summary.subscription_id,
            user=self.user,
            plan=self.plan_pro,
        )
        mock_get_or_create.return_value = (fake_sub, True)

        result = create_subscription(self.summary)

        self.assertEqual(result, fake_sub)
        mock_get_or_create.assert_called_once()
        _, kwargs = mock_get_or_create.call_args
        self.assertEqual(kwargs["stripe_subscription_id"], self.summary.subscription_id)
        self.assertIn("defaults", kwargs)

    @patch.object(Subscription.objects, "get_or_create")
    def test_get_or_create_defaults_payload_is_correct(self, mock_get_or_create):
        fake_sub = SubscriptionFactory.build(
            stripe_subscription_id=self.summary.subscription_id,
            user=self.user,
            plan=self.plan_pro,
        )
        mock_get_or_create.return_value = (fake_sub, True)

        create_subscription(self.summary)

        _, kwargs = mock_get_or_create.call_args
        defaults = kwargs["defaults"]

        self.assertEqual(defaults["user"], self.user)
        self.assertEqual(defaults["plan"], self.plan_pro)
        self.assertEqual(defaults["billing_cycle"], self.summary.billing_cycle_interval)
        self.assertEqual(defaults["start_date"], self.summary.billing_cycle_start)
        self.assertEqual(defaults["end_date"], self.summary.billing_cycle_end)
        self.assertIsNone(defaults["trial_start_date"])
        self.assertTrue(defaults["is_recurring"])

    def test_different_subscription_id_creates_new_subscription(self):
        s1 = create_subscription(self.summary)

        summary2 = SubscriptionSummary(
            **{**self.summary.__dict__, "subscription_id": "sub_456"}
        )
        s2 = create_subscription(summary2)

        self.assertEqual(Subscription.objects.count(), 2)
        self.assertNotEqual(s1.id, s2.id)
        self.assertEqual(s2.stripe_subscription_id, "sub_456")

    @patch("apps.subscriptions.services.subscriptions.create_subscription.get_plan")
    def test_plan_change_does_not_create_duplicate_if_subscription_id_same(
            self, mock_get_plan
    ):
        # First call uses plan1
        mock_get_plan.return_value = self.plan_pro
        sub1 = create_subscription(self.summary)

        # Second call: same subscription_id, but different plan_id in summary and get_plan returns plan2
        mock_get_plan.return_value = self.plan_pro
        summary2 = SubscriptionSummary(
            **{**self.summary.__dict__, "plan_id": "price_999"}
        )
        sub2 = create_subscription(summary2)

        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(sub1.id, sub2.id)

        # And because get_or_create doesn't update defaults when created=False:
        sub2.refresh_from_db()
        self.assertEqual(sub2.plan_id, self.plan_pro.id)
