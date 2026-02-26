from types import SimpleNamespace

from django.core import mail
from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.constants.stripe_invoice import SUBSCRIPTION_CYCLE
from apps.payments.factories.payment import PaymentFactory
from apps.payments.services.invoices.failed_payment import apply_payment_failed
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionProPlanFactory
from apps.users.factories.user_factory import UserFactory


class TestFailedPayment(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="dias",
            email="dias@example.com",
            password="pass12345",
        )

        cls.subscription = SubscriptionProPlanFactory(
            user=cls.user, stripe_subscription_id="sub123"
        )

        cls.payment = PaymentFactory(
            user=cls.user,
            subscription=cls.subscription,
            stripe_invoice_id="in_123",
            amount=10,
        )

    def test_apply_payment_failed(self):
        invoice_summary = SimpleNamespace(
            invoice_id=self.payment.stripe_invoice_id,
            billing_reason=SUBSCRIPTION_CYCLE,
        )

        apply_payment_failed(invoice_summary)

        self.payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatusChoices.RETRYING.value)
        self.assertEqual(
            self.subscription.status, SubscriptionStatusChoices.PAST_DUE.value
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_apply_payment_failed_no_billing_cycle(self):
        invoice_summary = SimpleNamespace(
            invoice_id=self.payment.stripe_invoice_id,
            billing_reason=None,
        )

        payment_status = self.payment.status
        subscription_status = self.subscription.status

        apply_payment_failed(invoice_summary)

        self.payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(self.payment.status, payment_status)
        self.assertEqual(self.subscription.status, subscription_status)
        self.assertEqual(len(mail.outbox), 0)
