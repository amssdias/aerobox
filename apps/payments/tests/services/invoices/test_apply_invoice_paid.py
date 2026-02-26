from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary
from apps.payments.choices.payment_choices import PaymentMethodChoices, PaymentStatusChoices
from apps.payments.factories.payment import PaymentFactory
from apps.payments.services.invoices.apply_invoice_paid import apply_invoice_paid
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionProPlanFactory, SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class TestApplyInvoicePaid(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            username="dias",
            email="dias@example.com",
            password="pass12345",
        )

        cls.free_sub = SubscriptionFreePlanFactory(
            user=cls.user,
        )

        cls.subscription = SubscriptionProPlanFactory(
            user=cls.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
        )

        cls.payment = PaymentFactory(
            user=cls.user,
            subscription=cls.subscription,
            stripe_invoice_id="in_123",
            amount=10,
        )

    @staticmethod
    def _create_invoice_summary(
            invoice_id,
            subscription_id="sub_123",
            payment_method_type=PaymentMethodChoices.CARD.value,
            amount_paid=1000,
            amount_due=1000,
            paid_at=timezone.now(),
            hosted_invoice_url="https://stripe.example/invoice/in_123",
            invoice_pdf="https://stripe.example/invoice/in_123.pdf",
            billing_reason=None,
            subscription_period_end_date=timezone.now() + timedelta(days=30),
    ):
        return InvoicePaymentSummary(
            invoice_id=invoice_id,
            subscription_id=subscription_id,
            payment_method_type=payment_method_type,
            amount_paid=amount_paid,
            amount_due=amount_due,
            paid_at=paid_at,
            hosted_invoice_url=hosted_invoice_url,
            invoice_pdf=invoice_pdf,
            billing_reason=billing_reason,
            subscription_period_end_date=subscription_period_end_date,
        )

    def test_apply_invoice_paid_updates_payment_and_triggers_side_effects(self):
        invoice_summary = self._create_invoice_summary(invoice_id=self.payment.stripe_invoice_id)

        apply_invoice_paid(invoice_summary)

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, PaymentMethodChoices.CARD.value)
        self.assertEqual(self.payment.payment_date.day, invoice_summary.paid_at.day)
        self.assertEqual(self.payment.status, PaymentStatusChoices.PAID.value)
        self.assertEqual(self.payment.amount, 10.0)
        self.assertEqual(self.payment.invoice_url, invoice_summary.hosted_invoice_url)
        self.assertEqual(self.payment.invoice_pdf_url, invoice_summary.invoice_pdf)

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, SubscriptionStatusChoices.ACTIVE.value)
        self.assertEqual(self.subscription.end_date.month, invoice_summary.subscription_period_end_date.month)

        self.free_sub.refresh_from_db()
        self.assertEqual(self.free_sub.status, SubscriptionStatusChoices.INACTIVE.value)

        self.assertEqual(len(mail.outbox), 1)

    @patch("apps.payments.services.invoices.apply_invoice_paid.logger.error")
    def test_apply_invoice_paid_cannot_update_missing_payment_method(self, mock_logger):
        invoice_summary = self._create_invoice_summary(
            invoice_id=self.payment.stripe_invoice_id,
            payment_method_type=None
        )

        with self.assertRaises(ValueError):
            apply_invoice_paid(invoice_summary)
            mock_logger.assert_called_once()

    def test_apply_invoice_paid_cannot_update_missing_amount(self):
        invoice_summary = self._create_invoice_summary(
            invoice_id=self.payment.stripe_invoice_id,
            amount_paid=None
        )

        with self.assertRaises(ValueError):
            apply_invoice_paid(invoice_summary)

    def test_apply_invoice_paid_cannot_update_amount_less_than_zero(self):
        invoice_summary = self._create_invoice_summary(
            invoice_id=self.payment.stripe_invoice_id,
            amount_paid=-1
        )

        with self.assertRaises(ValueError):
            apply_invoice_paid(invoice_summary)

    @patch("apps.payments.services.invoices.apply_invoice_paid.logger.error")
    def test_apply_invoice_paid_cannot_update_amount_different_from_payment(self, mock_logger):
        invoice_summary = self._create_invoice_summary(
            invoice_id=self.payment.stripe_invoice_id,
            amount_paid=100000,
        )

        with self.assertRaises(ValueError):
            apply_invoice_paid(invoice_summary)
            mock_logger.assert_called_once()
