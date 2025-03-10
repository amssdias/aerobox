from datetime import datetime
from unittest.mock import patch

from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.services.stripe_events.stripe_subscription_deleted import (
    SubscriptionDeleteddHandler,
)
from apps.users.factories.user_factory import UserFactory


class SubscriptionDeletedHandlerTest(TestCase):

    def setUp(self):
        self.user = UserFactory(username="testuser")

        self.plan = PlanFactory(name="Test Plan", stripe_price_id="price_test")
        self.subscription = SubscriptionFactory(
            user=self.user,
            plan=self.plan,
        )

        self.data = {
            "id": self.subscription.stripe_subscription_id,
            "ended_at": 1702592000,
        }
        self.handler = SubscriptionDeleteddHandler({"data": {"object": self.data}})

    def test_process_success(self):
        self.handler.process()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.CANCELED.value
        )
        self.assertEqual(
            self.subscription.end_date, datetime.utcfromtimestamp(1702592000).date()
        )

    def test_process_no_ended_at(self):
        self.handler.data["ended_at"] = None
        self.handler.process()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.CANCELED.value
        )

    @patch("config.services.stripe_services.stripe_events.customer_event.logger.error")
    def test_process_subscription_does_not_exist(self, mock_logger):
        self.handler.data["id"] = "non_existent_sub"

        self.handler.process()
        mock_logger.called_once_with(
            "Subscription does not exist",
            extra={"stripe_subscription_id": self.subscription.stripe_subscription_id},
        )

    def test_process_subscription_without_ended_at(self):
        del self.handler.data["ended_at"]
        self.handler.process()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.CANCELED.value
        )

    def test_cancel_pending_payments_updates_only_pending(self):
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
