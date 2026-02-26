from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.payments.models import Payment
from apps.payments.services.invoices.ensure_payment import get_or_sync_payment_from_stripe, create_payment_from_stripe
from apps.subscriptions.factories.subscription import SubscriptionProPlanFactory
from apps.users.factories.user_factory import UserFactory


class TestEnsurePayment(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="dias",
            email="dias@example.com",
            password="pass12345",
        )

        cls.subscription = SubscriptionProPlanFactory(
            user=cls.user,
            stripe_subscription_id="sub123"
        )

        cls.payment = PaymentFactory(
            user=cls.user,
            subscription=cls.subscription,
            stripe_invoice_id="in_123",
            amount=10,
        )

    def test_get_or_sync_payment_from_stripe(self):
        invoice_summary = SimpleNamespace(
            invoice_id=self.payment.stripe_invoice_id,
        )
        payment = get_or_sync_payment_from_stripe(invoice_summary)

        self.assertEqual(payment.id, self.payment.id)

    @patch("apps.payments.services.invoices.ensure_payment.create_payment_from_stripe")
    def test_get_or_sync_payment_from_stripe_creates_payment(self, mock_create_payment_from_stripe):
        invoice_summary = SimpleNamespace(
            invoice_id=None,
        )
        mock_create_payment_from_stripe.return_value = self.payment

        payment = get_or_sync_payment_from_stripe(invoice_summary)

        mock_create_payment_from_stripe.assert_called_once()
        self.assertEqual(payment.id, self.payment.id)

    @patch("apps.payments.services.invoices.ensure_payment.get_stripe_invoice")
    @patch("apps.payments.services.invoices.ensure_payment.to_invoice_payment_summary")
    @patch("apps.payments.services.invoices.ensure_payment.create_invoice")
    def test_create_payment_from_stripe_assert_calls(self, mock_create_invoice, mock_to_invoice_payment_summary,
                                                     mock_get_stripe_invoice):
        create_payment_from_stripe("in_123")

        mock_get_stripe_invoice.assert_called_once()
        mock_to_invoice_payment_summary.assert_called_once()
        mock_create_invoice.assert_called_once()

    @patch("apps.payments.services.invoices.ensure_payment.get_stripe_invoice")
    @patch("apps.payments.services.invoices.ensure_payment.to_invoice_payment_summary")
    def test_create_payment_from_stripe(self, mock_to_invoice_payment_summary, mock_get_stripe_invoice):
        invoice_summary = SimpleNamespace(
            invoice_id="in_1234",
            subscription_id=self.subscription.stripe_subscription_id,
            amount_paid=1000,
            hosted_invoice_url=None,
            invoice_pdf=None,
        )

        n_payments = Payment.objects.count()

        mock_to_invoice_payment_summary.return_value = invoice_summary

        payment = create_payment_from_stripe("in_1234")

        mock_get_stripe_invoice.assert_called_once()
        mock_to_invoice_payment_summary.assert_called_once()

        self.assertEqual(Payment.objects.count(), n_payments + 1)
        self.assertEqual(payment.stripe_invoice_id, invoice_summary.invoice_id)
        self.assertEqual(payment.status, PaymentStatusChoices.PENDING.value)
        self.assertIsNone(payment.invoice_url)
        self.assertIsNone(payment.invoice_pdf_url)
        self.assertEqual(payment.amount, 10.00)
