from datetime import date, timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase

from apps.integrations.stripe.subscriptions.dto.subscription import SubscriptionSummary
from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.plan_factory import PlanProFactory
from apps.subscriptions.factories.subscription import (
    SubscriptionFactory,
    SubscriptionFreePlanFactory,
)
from apps.subscriptions.services.subscriptions.cancel_subscription import (
    cancel_subscription,
    reactivate_free_subscription,
)
from apps.users.factories.user_factory import UserFactory


class CancelSubscriptionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.plan = PlanProFactory(stripe_price_id="price_123")
        cls.subscription = SubscriptionFactory(
            stripe_subscription_id="sub_123",
            user=cls.user,
            plan=cls.plan,
            status=SubscriptionStatusChoices.ACTIVE.value,
            end_date=None,
        )

    def setUp(self) -> None:
        today = date.today()
        self.summary = SubscriptionSummary(
            subscription_id=self.subscription.stripe_subscription_id,
            customer_id=self.user.profile.stripe_customer_id,
            plan_id=self.plan.stripe_price_id,
            billing_cycle_start=today,
            billing_cycle_end=today + timedelta(days=30),
            billing_cycle_interval="month",
            cancel_at_period_end=None,
            ended_at=today,
        )

    def test_cancel_subscription(self):
        pending = PaymentFactory(
            subscription=self.subscription,
            user=self.user,
            status=PaymentStatusChoices.PENDING.value,
        )
        paid = PaymentFactory(
            subscription=self.subscription,
            user=self.user,
            status=PaymentStatusChoices.PAID.value,
        )

        cancel_subscription(self.summary)

        self.subscription.refresh_from_db()
        pending.refresh_from_db()
        paid.refresh_from_db()

        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.CANCELED.value
        )
        self.assertEqual(self.subscription.end_date, self.summary.ended_at)
        self.assertEqual(pending.status, PaymentStatusChoices.CANCELED.value)
        self.assertEqual(paid.status, PaymentStatusChoices.PAID.value)
        self.assertEqual(len(mail.outbox), 1)

    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.send_subscription_cancelled_email.delay"
    )
    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.cancel_pending_payments"
    )
    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.logger.warning"
    )
    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.get_subscription"
    )
    def test_cancel_subscription_when_missing_logs_and_returns(
            self,
            mock_get_subscription,
            mock_logger_warning,
            mock_cancel_pending_payments,
            mock_email_delay,
    ):
        mock_get_subscription.return_value = None

        cancel_subscription(self.summary)

        mock_logger_warning.assert_called_once()
        mock_cancel_pending_payments.assert_not_called()
        mock_email_delay.assert_not_called()

    def test_cancel_subscription_updates_status_and_end_date(self):
        subscription = cancel_subscription(self.summary)

        subscription.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionStatusChoices.CANCELED.value)
        self.assertEqual(subscription.end_date, self.summary.ended_at)

    def test_reactivate_free_subscription_activates_free_sub_when_exists(self):
        user = UserFactory()
        plan = PlanProFactory(stripe_price_id="price_123")
        free_subscription = SubscriptionFreePlanFactory(
            user=user,
            status=SubscriptionStatusChoices.INACTIVE.value,
            end_date=None,
        )
        subscription = SubscriptionFactory(
            stripe_subscription_id="sub_12345",
            user=user,
            plan=plan,
            status=SubscriptionStatusChoices.ACTIVE.value,
            end_date=None,
        )

        reactivate_free_subscription(subscription)

        free_subscription.refresh_from_db()
        self.assertEqual(
            free_subscription.status, SubscriptionStatusChoices.ACTIVE.value
        )

    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.logger.warning"
    )
    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.get_free_subscription"
    )
    def test_reactivate_free_subscription_logs_warning_when_missing(
            self, mock_get_free_subscription, mock_logger_warning
    ):
        mock_get_free_subscription.return_value = None

        reactivate_free_subscription(self.subscription)

        mock_logger_warning.assert_called_once()

    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.send_subscription_cancelled_email.delay"
    )
    @patch(
        "apps.subscriptions.services.subscriptions.cancel_subscription.cancel_pending_payments"
    )
    def test_cancel_subscription_calls_payment_cancel_and_email(
            self,
            mock_cancel_pending_payments,
            mock_email_delay,
    ):
        free_subscription = SubscriptionFreePlanFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
            end_date=None,
        )

        cancel_subscription(self.summary)

        mock_cancel_pending_payments.assert_called_once()
        mock_email_delay.assert_called_once_with(self.user.id)
