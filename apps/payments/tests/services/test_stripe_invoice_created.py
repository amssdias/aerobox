from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.payments.choices.payment_choices import PaymentStatusChoices
from apps.payments.models import Payment
from apps.payments.services.stripe_events.invoice_created import InvoiceCreatedHandler
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory


class InvoiceCreatedHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.subscription = SubscriptionFactory()
        cls.user = cls.subscription.user

    def setUp(self):
        # Patch stripe.Invoice.retrieve globally for this class
        patcher = patch("stripe.Invoice.retrieve")
        self.mock_retrieve_invoice = patcher.start()
        self.addCleanup(patcher.stop)  # Ensures patch is removed after each test

        self.data = {
            "data": {
                "object": {
                    "id": "invoice_123",
                    "amount_due": 499,
                    "customer": self.user.profile.stripe_customer_id,
                    "status": "open",
                    "hosted_invoice_url": "https://stripe.com/invoice_123",
                    "invoice_pdf": "https://stripe.com/invoice_123.pdf",
                    "parent": {
                        "subscription_details": {
                            "subscription": self.subscription.stripe_subscription_id
                        }
                    }
                }
            }
        }
        self.stripe_invoice_mock = MagicMock(**self.data["data"]["object"])
        self.stripe_invoice_mock.parent = self.data["data"]["object"]["parent"]
        self.stripe_invoice_mock.amount_paid = None

        self.mock_retrieve_invoice.return_value = self.stripe_invoice_mock

        self.handler = InvoiceCreatedHandler(self.data)

    def test_process_valid_payment(self):
        self.handler.process()

        invoice_id = self.data.get("data", {}).get("object", {}).get("id")
        self.assertTrue(Payment.objects.filter(stripe_invoice_id=invoice_id).exists())

        payment = Payment.objects.get(stripe_invoice_id=invoice_id)
        self.assertEqual(payment.status, PaymentStatusChoices.PENDING.value)

    def test_get_invoice_id(self):
        self.assertEqual(self.handler.get_invoice_id(), "invoice_123")

    def test_get_invoice_id_raises_error_when_id_missing(self):
        del self.handler.data["id"]

        with self.assertRaises(ValueError) as context:
            self.handler.get_invoice_id()

    def test_get_subscription_id_from_invoice(self):
        subscription_id = self.handler.data.get("parent").get("subscription_details").get("subscription")
        invoice_subscription_id = self.handler.get_subscription_id_from_invoice(self.stripe_invoice_mock)

        self.assertEqual(invoice_subscription_id, subscription_id)

    @patch("apps.payments.services.stripe_events.invoice_created.logger.warning")
    def test_get_subscription_id_logs_error_if_missing(self, mock_logger):
        result = self.handler.get_subscription(None)

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    @patch("stripe.Subscription.retrieve")
    @patch.object(InvoiceCreatedHandler, "get_subscription")
    def test_create_subscription_for_already_created_subscription(self, mock_get_subscription, subscription_mock):
        mock_get_subscription.return_value = None
        plan = PlanFactory(name="Test Plan", stripe_price_id="price_test")
        data = {
            "id": self.subscription.stripe_subscription_id,
            "customer": self.user.profile.stripe_customer_id,
            "status": "incomplete",
            "plan": {"id": plan.stripe_price_id},
            "items": {
                "data": [
                    {
                        "current_period_start": 1700000000,
                        "current_period_end": 1702592000,
                        "plan": {
                            "interval": "month"
                        }
                    }
                ]
            }
        }
        subscription_mock_object = MagicMock(**data)
        subscription_mock_object.get.return_value = data["items"]
        subscription_mock.return_value = subscription_mock_object

        subscription = self.handler.get_or_create_subscription(
            stripe_subscription_id=self.subscription.stripe_subscription_id)

        self.assertTrue(subscription)
        self.assertEqual(subscription.stripe_subscription_id, self.subscription.stripe_subscription_id)

    def test_is_valid_payment_returns_true_for_valid_data(self):
        result = self.handler.is_valid_payment(
            self.user,
            self.subscription,
            "invoice_123",
            5,
        )

        self.assertTrue(result)

    def test_is_valid_payment_returns_false_if_user_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                None, self.subscription, "invoice_123", 4.99
            )

    def test_is_valid_payment_returns_false_if_subscription_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                self.user, None, "invoice_123", 4.99
            )

    def test_is_valid_payment_returns_false_if_amount_due_missing(self):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(
                self.user, self.subscription, "invoice_123", None
            )

    def test_create_payment_creates_payment_successfully(self):
        self.handler.create_payment(
            user=self.user,
            subscription=self.subscription,
            status=PaymentStatusChoices.PENDING.value,
            stripe_invoice_id="invoice_123",
            invoice_url="https://stripe.com/invoice_123",
            invoice_pdf_url="https://stripe.com/invoice_123.pdf",
            amount=4.99,
        )

        self.assertTrue(
            Payment.objects.filter(stripe_invoice_id="invoice_123").exists()
        )

    @patch("apps.payments.services.stripe_events.invoice_created.logger.critical")
    def test_is_valid_payment_logs_critical_error_if_missing_fields(self, mock_logger):
        with self.assertRaises(RuntimeError) as context:
            self.handler.is_valid_payment(None, None, None, None)

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_created.logger.info")
    def test_create_payment_logs_success_message(self, mock_logger):
        self.handler.create_payment(
            user=self.user,
            subscription=self.subscription,
            status=PaymentStatusChoices.PENDING.value,
            stripe_invoice_id="invoice_123",
            invoice_url="https://stripe.com/invoice_123",
            invoice_pdf_url="https://stripe.com/invoice_123.pdf",
            amount=4.99,
        )

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_events.invoice_created.SubscriptionCreateddHandler")
    def test_invoice_creation_with_missing_subscription(self, mock_handler_class):
        mock_handler_instance = MagicMock()
        mock_handler_class.return_value = mock_handler_instance
        mock_handler_instance.create_subscription.return_value = 'mocked-subscription'

        self.handler.get_or_create_subscription(stripe_subscription_id=None)

        mock_handler_instance.create_subscription.assert_called_once_with(None)
