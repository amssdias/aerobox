from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary
from apps.payments.choices.payment_choices import PaymentMethodChoices, PaymentStatusChoices
from apps.payments.models import Payment
from apps.payments.services.invoices.create_invoice import create_invoice
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionProPlanFactory, SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class TestCreateInvoice(TestCase):

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
            stripe_subscription_id="sub123"
        )

    @staticmethod
    def _create_invoice_summary(
            subscription_id,
            invoice_id="inv_123",
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

    def test_create_invoice_success(self):
        invoice_summary = self._create_invoice_summary(
            subscription_id=self.subscription.stripe_subscription_id
        )

        n_payments = Payment.objects.count()

        create_invoice(invoice_summary)

        self.assertEqual(Payment.objects.count(), n_payments + 1)

        payment = Payment.objects.get(stripe_invoice_id=invoice_summary.invoice_id)
        self.assertEqual(payment.status, PaymentStatusChoices.PENDING.value)
        self.assertEqual(payment.invoice_url, invoice_summary.hosted_invoice_url)
        self.assertEqual(payment.invoice_pdf_url, invoice_summary.invoice_pdf)
        self.assertEqual(payment.amount, 10.00)

    def test_create_invoice_missing_amount_paid(self):
        invoice_summary = self._create_invoice_summary(
            subscription_id=self.subscription.stripe_subscription_id,
            amount_paid=None,
        )

        n_payments = Payment.objects.count()

        create_invoice(invoice_summary)

        self.assertEqual(Payment.objects.count(), n_payments + 1)

        payment = Payment.objects.get(stripe_invoice_id=invoice_summary.invoice_id)
        self.assertEqual(payment.status, PaymentStatusChoices.PENDING.value)
        self.assertEqual(payment.invoice_url, invoice_summary.hosted_invoice_url)
        self.assertEqual(payment.invoice_pdf_url, invoice_summary.invoice_pdf)
        self.assertEqual(payment.amount, 10.00)

    def test_create_invoice_missing_amount_due(self):
        invoice_summary = self._create_invoice_summary(
            subscription_id=self.subscription.stripe_subscription_id,
            amount_due=None,
        )

        n_payments = Payment.objects.count()

        create_invoice(invoice_summary)

        self.assertEqual(Payment.objects.count(), n_payments + 1)

        payment = Payment.objects.get(stripe_invoice_id=invoice_summary.invoice_id)
        self.assertEqual(payment.status, PaymentStatusChoices.PENDING.value)
        self.assertEqual(payment.invoice_url, invoice_summary.hosted_invoice_url)
        self.assertEqual(payment.invoice_pdf_url, invoice_summary.invoice_pdf)
        self.assertEqual(payment.amount, 10.00)

    def test_create_invoice_missing_amount_paid_and_due(self):
        invoice_summary = self._create_invoice_summary(
            subscription_id=self.subscription.stripe_subscription_id,
            amount_due=None,
            amount_paid=None,
        )

        n_payments = Payment.objects.count()

        with self.assertRaises(ValueError):
            create_invoice(invoice_summary)

        self.assertEqual(Payment.objects.count(), n_payments)

    def test_create_invoice_amount_paid_less_then_zero(self):
        invoice_summary = self._create_invoice_summary(
            subscription_id=self.subscription.stripe_subscription_id,
            amount_paid=-1,
            amount_due=None,
        )

        n_payments = Payment.objects.count()

        with self.assertRaises(ValueError):
            create_invoice(invoice_summary)

        self.assertEqual(Payment.objects.count(), n_payments)

    def test_create_invoice_amount_due_less_then_zero(self):
        invoice_summary = self._create_invoice_summary(
            subscription_id=self.subscription.stripe_subscription_id,
            amount_paid=None,
            amount_due=-1,
        )

        n_payments = Payment.objects.count()

        with self.assertRaises(ValueError):
            create_invoice(invoice_summary)

        self.assertEqual(Payment.objects.count(), n_payments)
