from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.payments.models import Payment
from apps.payments.services.invoices.cancel_payments import cancel_pending_payments
from apps.subscriptions.factories.subscription import SubscriptionFactory


class TestCancelPendingPayments(TestCase):

    def test_cancels_only_pending_and_retrying_payments(self):
        subscription = SubscriptionFactory()

        p1 = PaymentFactory(subscription=subscription, status=PaymentStatusChoices.PENDING.value)
        p2 = PaymentFactory(subscription=subscription, status=PaymentStatusChoices.RETRYING.value)
        p3 = PaymentFactory(subscription=subscription, status=PaymentStatusChoices.PAID.value)

        qs = Payment.objects.filter(subscription=subscription)

        cancel_pending_payments(payments=qs, subscription_id=str(subscription.id))

        p1.refresh_from_db()
        p2.refresh_from_db()
        p3.refresh_from_db()

        self.assertEqual(p1.status, PaymentStatusChoices.CANCELED.value)
        self.assertEqual(p2.status, PaymentStatusChoices.CANCELED.value)
        self.assertEqual(p3.status, PaymentStatusChoices.PAID.value)

    def test_cancel_pending_payments_does_nothing_when_paid_exist(self):
        subscription = SubscriptionFactory()

        p1 = PaymentFactory(subscription=subscription, status=PaymentStatusChoices.PENDING.value)
        p2 = PaymentFactory(subscription=subscription, status=PaymentStatusChoices.PAID.value)

        qs = Payment.objects.filter(subscription=subscription)

        cancel_pending_payments(payments=qs, subscription_id=str(subscription.id))

        p1.refresh_from_db()
        p2.refresh_from_db()

        self.assertEqual(p1.status, PaymentStatusChoices.CANCELED.value)
        self.assertEqual(p2.status, PaymentStatusChoices.PAID.value)
