from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock

from apps.subscriptions.services.stripe_events.stripe_subscription import (
    SubscriptiondHandler,
)
from config.services.stripe_services.stripe_service import StripeService


class StripeServiceTest(SimpleTestCase):

    def setUp(self):
        self.stripe_service = StripeService()
        self.event_customer_subscription_created = "customer.subscription.created"
        self.event_customer_subscription_deleted = "customer.subscription.deleted"

    @patch(
        "apps.subscriptions.services.stripe_events.stripe_subscription.SubscriptiondHandler.process"
    )
    def test_process_webhook_event_subscription_created(self, mock_process):
        event = {
            "type": self.event_customer_subscription_created,
            "data": {"object": {"id": "sub_123"}},
        }

        self.stripe_service.process_webhook_event(event)
        mock_process.assert_called_once()

    @patch(
        "apps.subscriptions.services.stripe_events.stripe_subscription_deleted.SubscriptionDeleteddHandler.process"
    )
    def test_process_webhook_event_subscription_deleted(self, mock_process):
        event = {
            "type": self.event_customer_subscription_deleted,
            "data": {"object": {"id": "sub_456"}},
        }

        self.stripe_service.process_webhook_event(event)
        mock_process.assert_called_once()

    @patch("config.services.stripe_services.stripe_service.logger.error")
    def test_process_webhook_event_unknown_event(self, mock_logger):
        event = {"type": "invoice.unknown.event", "data": {"object": {"id": "inv_789"}}}

        self.stripe_service.process_webhook_event(event)
        mock_logger.assert_called_once_with(f"Unhandled event type: {event}")

    def test_get_handler_valid_event(self):
        event = {
            "type": self.event_customer_subscription_created,
            "data": {"object": {"id": "sub_123"}},
        }
        handler = self.stripe_service.get_handler(
            self.event_customer_subscription_created, event
        )

        self.assertIsInstance(handler, SubscriptiondHandler)

    def test_get_handler_invalid_event(self):
        event = {"type": "invalid.event", "data": {"object": {"id": "inv_789"}}}
        handler = self.stripe_service.get_handler("invalid.event", event)

        self.assertIsNone(handler)

    def test_get_handler_missing_event_type(self):
        event = {"data": {"object": {"id": "sub_123"}}}
        with self.assertRaises(KeyError):
            self.stripe_service.get_handler(event["type"], event)

    @patch("config.services.stripe_services.stripe_service.StripeService.get_handler")
    def test_process_webhook_event_with_mocked_handler(self, mock_get_handler):
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler

        event = {
            "type": self.event_customer_subscription_created,
            "data": {"object": {"id": "sub_123"}},
        }
        self.stripe_service.process_webhook_event(event)

        mock_handler.process.assert_called_once()

    @patch(
        "config.services.stripe_services.stripe_service.StripeService.get_handler",
        return_value=None,
    )
    @patch("config.services.stripe_services.stripe_service.logger.error")
    def test_process_webhook_event_no_handler(self, mock_logger, mock_get_handler):
        event = {"type": "random.event", "data": {"object": {"id": "inv_789"}}}

        self.stripe_service.process_webhook_event(event)

        mock_logger.assert_called_once_with(f"Unhandled event type: {event}")
        mock_get_handler.assert_called_once_with("random.event", event)

    @patch("config.services.stripe_services.stripe_service.logger.error")
    def test_process_webhook_event_missing_type(self, mock_logger):
        event = {"data": self.event_customer_subscription_created}

        with self.assertRaises(KeyError):
            self.stripe_service.process_webhook_event(event)

        mock_logger.assert_called_once_with(
            "Webhook event missing required 'type' field.", extra={"event": event}
        )

    @patch("config.services.stripe_services.stripe_service.logger.error")
    def test_process_webhook_event_missing_data(self, mock_logger):
        event = {"type": self.event_customer_subscription_created}

        with self.assertRaises(KeyError):
            self.stripe_service.process_webhook_event(event)

        mock_logger.assert_called_once_with(
            "Webhook event missing required 'data' field.", extra={"event": event}
        )

    @patch("config.services.stripe_services.stripe_service.logger.error")
    def test_process_webhook_event_empty_data(self, mock_logger):
        event = {"type": self.event_customer_subscription_created, "data": {}}

        with self.assertRaises(KeyError):
            self.stripe_service.process_webhook_event(event)

        mock_logger.assert_called_once_with(
            "Webhook event missing required 'data' field.", extra={"event": event}
        )

    @patch("config.services.stripe_services.stripe_service.logger.error")
    def test_process_webhook_event_missing_object(self, mock_logger):
        event = {
            "type": self.event_customer_subscription_created,
            "data": {"other_object": ""},
        }

        with self.assertRaises(KeyError):
            self.stripe_service.process_webhook_event(event)

        mock_logger.assert_called_once_with(
            "Webhook event missing required 'data.object' field.",
            extra={"event": event},
        )

    def test_process_webhook_event_empty_event(self):
        event = {}

        with self.assertRaises(KeyError):
            self.stripe_service.process_webhook_event(event)
