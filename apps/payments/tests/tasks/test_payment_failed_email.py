from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.translation import override, gettext as _

from apps.payments.tasks.send_payment_failed_email import send_invoice_payment_failed_email
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class SendInvoicePaymentFailedEmailTests(TestCase):

    def setUp(self):
        self.user = UserFactory(email="test@example.com")
        self.user.profile.language = "en"
        self.user.profile.save()

    @patch("apps.payments.tasks.send_payment_failed_email.EmailMultiAlternatives.send")
    def test_sends_email_when_user_has_inactive_subscription(self, mock_send):
        SubscriptionFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
            end_date=timezone.now().date()
        )

        result = send_invoice_payment_failed_email(str(self.user.id))

        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch("apps.payments.tasks.send_payment_failed_email.logger")
    def test_returns_none_and_logs_when_user_does_not_exist(self, mock_logger):
        result = send_invoice_payment_failed_email("10000")

        self.assertIsNone(result)
        mock_logger.warning.assert_called_once_with(
            "User with ID 10000 does not exist. Email payment failed not sent."
        )

    @patch("apps.payments.tasks.send_payment_failed_email.EmailMultiAlternatives.send")
    @patch("apps.payments.tasks.send_payment_failed_email.logger")
    def test_does_not_send_email_when_no_inactive_subscription(self, mock_logger, mock_send):
        SubscriptionFactory(
            user=self.user,
            status=SubscriptionStatusChoices.ACTIVE.value,
            end_date=timezone.now().date()
        )

        result = send_invoice_payment_failed_email(str(self.user.id))

        self.assertIsNone(result)
        mock_send.assert_not_called()
        mock_logger.info.assert_any_call(
            f"No active subscription found for user {self.user.email}. Email not sent."
        )

    @patch("apps.payments.tasks.send_payment_failed_email.EmailMultiAlternatives.send",
           side_effect=Exception("SMTP error"))
    @patch("apps.payments.tasks.send_payment_failed_email.logger")
    def test_logs_error_when_email_send_fails(self, mock_logger, mock_send):
        SubscriptionFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
            end_date=timezone.now().date()
        )

        result = send_invoice_payment_failed_email(str(self.user.id))

        self.assertIsNone(result)
        mock_logger.error.assert_called_once()
        self.assertIn("Failed to send payment failed email.", mock_logger.error.call_args[0][0])

    @override_settings(LANGUAGE_CODE="en")
    def test_email_sent_with_correct_language_content(self):
        self.user.profile.language = "es"
        self.user.profile.save()

        SubscriptionFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
            end_date=timezone.now().date()
        )

        send_invoice_payment_failed_email(str(self.user.id))

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        with override("es"):
            expected_subject = _("Payment Failed – Update Your Payment Method")

        self.assertEqual(sent_email.subject, expected_subject)
        self.assertIn(self.user.email, sent_email.to)
