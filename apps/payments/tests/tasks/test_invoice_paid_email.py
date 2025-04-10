# tests/test_tasks.py
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from apps.payments.tasks.send_invoice_paid_email import send_invoice_payment_success_email
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


@override_settings(FRONTEND_DOMAIN="https://frontend.example.com")
class SendInvoiceSuccessEmailTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")
        cls.invoice_url = "https://invoices.example.com/invoice123.pdf"

    def test_email_sent_successfully(self):
        result = send_invoice_payment_success_email(self.user.id, self.invoice_url)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Payment Successful", email.subject)
        self.assertIn(self.invoice_url, email.body)
        self.assertEqual(email.to, [self.user.email])
        self.assertEqual("text/html", email.alternatives[0][1])

    def test_email_content_contains_dashboard_url(self):
        send_invoice_payment_success_email(self.user.id, self.invoice_url)
        email = mail.outbox[0]
        self.assertIn(settings.FRONTEND_DOMAIN, email.alternatives[0][0])

    @patch("apps.payments.tasks.send_invoice_paid_email.logger.warning")
    def test_user_does_not_exist(self, mock_logger):
        result = send_invoice_payment_success_email(user_id=1000, invoice_pdf_url=self.invoice_url)
        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)
        mock_logger.assert_called_once()

    @patch("apps.payments.tasks.send_invoice_paid_email.EmailMultiAlternatives.send")
    def test_exception_logged_on_send_failure(self, mock_send):
        mock_send.side_effect = Exception("SMTP error")
        result = send_invoice_payment_success_email(self.user.id, self.invoice_url)
        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_language_override(self):
        self.user.profile.language = "es"
        self.user.profile.save()
        send_invoice_payment_success_email(self.user.id, self.invoice_url)
        email = mail.outbox[0]
        self.assertIn(self.invoice_url, email.body)
        self.assertIn("Pago Exitoso — Tu Factura Está Lista", email.subject)

    def test_multiple_emails_sent_independently(self):
        another_user = UserFactory(username="user2")
        another_user.profile.language = "es"
        another_user.profile.save()

        send_invoice_payment_success_email(self.user.id, self.invoice_url)
        send_invoice_payment_success_email(another_user.id, self.invoice_url)

        email_1 = mail.outbox[0]
        email_2 = mail.outbox[1]

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(email_1.to, [self.user.email])
        self.assertEqual(email_2.to, [another_user.email])

        self.assertIn("Payment Successful", email_1.subject)
        self.assertIn("Pago Exitoso — Tu Factura Está Lista", email_2.subject)
