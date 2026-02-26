from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.integrations.stripe.payments.dto.invoice import InvoicePaymentSummary
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import (
    SubscriptionFreePlanFactory,
    SubscriptionProPlanFactory,
)
from apps.subscriptions.services.subscriptions.apply_invoice_paid import (
    apply_invoice_paid_to_subscription,
    deactivate_existing_free_subscription,
)
from apps.users.factories.user_factory import UserFactory


class ApplyInvoicePaidToSubscriptionIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        today = timezone.now().date()
        cls.today = today
        cls.next_month = today + timedelta(days=30)
        cls.two_months = today + timedelta(days=60)

    def setUp(self):
        self.free_sub = SubscriptionFreePlanFactory(user=self.user)
        self.paid_sub = SubscriptionProPlanFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
            start_date=self.today,
            end_date=self.next_month,
        )

        self.invoice_summary = InvoicePaymentSummary(
            invoice_id="in_test_001",
            subscription_id=str(self.paid_sub.id),
            payment_method_type=None,
            amount_paid=None,
            amount_due=None,
            paid_at=None,
            hosted_invoice_url=None,
            invoice_pdf=None,
            billing_reason=None,
            subscription_period_end_date=self.two_months,
        )

    def test_apply_invoice_paid_activates_extends_and_deactivates_free(self):
        apply_invoice_paid_to_subscription(self.paid_sub, self.invoice_summary)

        self.paid_sub.refresh_from_db()
        self.free_sub.refresh_from_db()

        self.assertEqual(self.paid_sub.status, SubscriptionStatusChoices.ACTIVE.value)
        self.assertEqual(self.paid_sub.end_date, self.two_months)
        self.assertEqual(self.free_sub.status, SubscriptionStatusChoices.INACTIVE.value)

    def test_apply_invoice_paid_end_date_already_matches_still_deactivates_free(self):
        self.paid_sub.end_date = self.two_months
        self.paid_sub.save()

        apply_invoice_paid_to_subscription(self.paid_sub, self.invoice_summary)

        self.paid_sub.refresh_from_db()
        self.free_sub.refresh_from_db()

        self.assertEqual(self.paid_sub.status, SubscriptionStatusChoices.ACTIVE.value)
        self.assertEqual(self.paid_sub.end_date, self.two_months)
        self.assertEqual(self.free_sub.status, SubscriptionStatusChoices.INACTIVE.value)

    def test_deactivate_existing_free_subscription_deactivates_free_subscription(self):
        deactivate_existing_free_subscription(self.paid_sub)

        self.free_sub.refresh_from_db()
        self.assertEqual(self.free_sub.status, SubscriptionStatusChoices.INACTIVE.value)

    def test_apply_invoice_paid_logs_extended_when_end_date_changes(self):
        with self.assertLogs("aerobox", level="INFO") as cm:
            apply_invoice_paid_to_subscription(self.paid_sub, self.invoice_summary)

        self.assertTrue(any("extended to" in msg for msg in cm.output))

    def test_apply_invoice_paid_logs_already_up_to_date_when_end_date_same(self):
        self.paid_sub.end_date = self.two_months
        self.paid_sub.save(update_fields=["end_date"])

        with self.assertLogs("aerobox", level="INFO") as cm:
            apply_invoice_paid_to_subscription(self.paid_sub, self.invoice_summary)

        self.assertTrue(any("already up to date" in msg for msg in cm.output))

    def test_apply_invoice_paid_keeps_free_inactive_if_already_inactive(self):
        self.free_sub.status = SubscriptionStatusChoices.INACTIVE.value
        self.free_sub.save(update_fields=["status"])

        apply_invoice_paid_to_subscription(self.paid_sub, self.invoice_summary)

        self.free_sub.refresh_from_db()
        self.assertEqual(self.free_sub.status, SubscriptionStatusChoices.INACTIVE.value)

    def test_deactivate_existing_free_subscription_when_no_free_subscription_logs_warning(
            self,
    ):
        self.free_sub.delete()

        with self.assertLogs("aerobox", level="WARNING") as cm:
            deactivate_existing_free_subscription(self.paid_sub)

        self.assertTrue(
            any(
                f"Subscription free does not exist for user {self.paid_sub.user.id}."
                in msg
                for msg in cm.output
            )
        )
