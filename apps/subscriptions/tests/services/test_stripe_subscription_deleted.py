from datetime import datetime
from unittest.mock import patch, MagicMock

from django.core import mail
from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.models import Plan
from apps.subscriptions.services.stripe_events.stripe_subscription_deleted import (
    SubscriptionDeleteddHandler,
)
from apps.users.factories.user_factory import UserFactory


class SubscriptionDeletedHandlerTest(TestCase):

    def setUp(self):
        self.user = UserFactory(username="testuser")

        self.plan = PlanFactory(name="Test Plan", stripe_price_id="price_test")
        self.free_plan = Plan.objects.get(is_free=True)
        self.free_subscription = SubscriptionFactory(
            user=self.user,
            plan=self.free_plan,
            status=SubscriptionStatusChoices.INACTIVE.value
        )

        self.subscription = SubscriptionFactory(
            user=self.user,
            plan=self.plan,
        )

        self.data = {
            "id": self.subscription.stripe_subscription_id,
            "ended_at": 1702592000,
        }
        self.handler = SubscriptionDeleteddHandler({"data": {"object": self.data}})

    @patch("stripe.Subscription.retrieve")
    def test_process_success(self, subscription_mock):
        subscription_mock.return_value = MagicMock(**self.data)

        self.handler.process()
        self.free_subscription.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.CANCELED.value
        )
        self.assertEqual(
            self.subscription.end_date, datetime.utcfromtimestamp(1702592000).date()
        )
        self.assertEqual(self.free_subscription.status, SubscriptionStatusChoices.ACTIVE.value)
        self.assertEqual(len(mail.outbox), 1)

    @patch("stripe.Subscription.retrieve")
    def test_process_no_ended_at(self, subscription_mock):
        subscription_mock.return_value = MagicMock(**{"ended_at": None})
        self.handler.process()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.CANCELED.value
        )

    @patch("config.services.stripe_services.stripe_events.subscription_mixin.logger.error")
    def test_process_subscription_does_not_exist(self, mock_logger):
        self.handler.data["id"] = "non_existent_sub"

        self.handler.process()
        mock_logger.called_once_with(
            "Subscription does not exist",
            extra={"stripe_subscription_id": self.subscription.stripe_subscription_id},
        )

    def test_cancel_pending_payments_updates_status_to_canceled(self):
        payment_1 = PaymentFactory(subscription=self.subscription)
        payment_2 = PaymentFactory(
            subscription=self.subscription, status=PaymentStatusChoices.RETRYING.value
        )
        canceled_payment = PaymentFactory(
            subscription=self.subscription, status=PaymentStatusChoices.CANCELED.value
        )
        completed_payment = PaymentFactory(
            subscription=self.subscription, status=PaymentStatusChoices.PAID.value
        )

        self.handler.cancel_pending_payments(self.subscription)

        payment_1.refresh_from_db()
        payment_2.refresh_from_db()
        canceled_payment.refresh_from_db()
        completed_payment.refresh_from_db()

        # Check pending payments are now canceled
        self.assertEqual(payment_1.status, PaymentStatusChoices.CANCELED.value)
        self.assertEqual(payment_2.status, PaymentStatusChoices.CANCELED.value)

        # Ensure completed and cancelled payments are not changed
        self.assertEqual(completed_payment.status, PaymentStatusChoices.PAID.value)
        self.assertEqual(canceled_payment.status, PaymentStatusChoices.CANCELED.value)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_deleted.logger.info")
    def test_cancel_pending_payments_logs_cancellation_count(self, mock_logger):
        pending_payment = PaymentFactory(subscription=self.subscription)
        retrying_payment = PaymentFactory(
            subscription=self.subscription, status=PaymentStatusChoices.RETRYING.value
        )
        canceled_payment = PaymentFactory(
            subscription=self.subscription, status=PaymentStatusChoices.CANCELED.value
        )
        completed_payment = PaymentFactory(
            subscription=self.subscription, status=PaymentStatusChoices.PAID.value
        )

        self.handler.cancel_pending_payments(self.subscription)

        pending_payment.refresh_from_db()
        retrying_payment.refresh_from_db()
        canceled_payment.refresh_from_db()
        completed_payment.refresh_from_db()

        mock_logger.assert_called_once_with(
            f"Canceled 2 pending payments for subscription ID: {self.subscription.id}"
        )

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_deleted.logger.info")
    def test_cancel_pending_payments_does_nothing_if_no_pending(self, mock_logger):
        self.handler.cancel_pending_payments(self.subscription)

        mock_logger.assert_not_called()

    def test_cancel_pending_payments_filters_only_pending_and_retrying(self):
        subscription = MagicMock()
        self.handler.cancel_pending_payments(subscription)

        subscription.payments.filter.assert_called_once_with(
            status__in=[
                PaymentStatusChoices.PENDING.value,
                PaymentStatusChoices.RETRYING.value,
            ]
        )

    def test_activate_free_subscription_sets_status_and_saves(self):
        self.handler.activate_free_subscription(self.free_subscription)
        self.free_subscription.refresh_from_db()
        self.assertEqual(self.free_subscription.status, SubscriptionStatusChoices.ACTIVE.value)

    def test_get_free_subscription_returns_correct_subscription(self):
        result = self.handler.get_free_subscription(self.subscription)
        self.assertTrue(result.plan.is_free)

    def test_get_free_subscription_returns_none_if_not_found(self):
        self.free_subscription.delete()
        result = self.handler.get_free_subscription(self.subscription)
        self.assertIsNone(result)

    def test_reactivate_free_subscription_if_exists_calls_activate(self):
        self.handler.reactivate_free_subscription_if_exists(self.subscription)
        self.free_subscription.refresh_from_db()

        self.assertEqual(self.free_subscription.status, SubscriptionStatusChoices.ACTIVE.value)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_deleted.logger.warning")
    def test_reactivate_free_subscription_if_not_exists_logs_warning(self, mock_logger):
        self.free_subscription.delete()
        self.handler.reactivate_free_subscription_if_exists(self.subscription)

        mock_logger.assert_called_once_with(
            "No free subscription found to reactivate for user %s.", self.user.id
        )
