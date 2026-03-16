from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from apps.payments.services.stripe_webhooks.dispatch import dispatch_stripe_event


class StripeServiceTest(SimpleTestCase):

    def setUp(self):
        self.event = {
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "data": 123,
                },
            },
        }
        self.event_customer_subscription_created = "customer.subscription.created"

    def test_dispatch_stripe_event_success(self):
        handler = Mock()

        with patch.dict(
                "apps.payments.services.stripe_webhooks.dispatch.HANDLERS",
                {"customer.subscription.created": handler},
                clear=True,
        ):
            dispatch_stripe_event(self.event)

        handler.assert_called_once()

    @patch("apps.payments.services.stripe_webhooks.dispatch.logger.info")
    def test_dispatch_stripe_event_not_found(self, mock_logger):
        self.event["type"] = "no.event.configured"
        handler = Mock()

        with patch.dict(
                "apps.payments.services.stripe_webhooks.dispatch.HANDLERS",
                {"customer.subscription.created": handler},
                clear=True,
        ):
            dispatch_stripe_event(self.event)

        handler.assert_not_called()
        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_webhooks.dispatch.logger.error")
    def test_dispatch_stripe_event_with_no_type(self, mock_logger):
        self.event["type"] = ""

        with self.assertRaises(KeyError):
            dispatch_stripe_event(self.event)

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_webhooks.dispatch.logger.error")
    def test_dispatch_stripe_event_with_no_event_data(self, mock_logger):
        self.event["data"] = {}

        with self.assertRaises(KeyError):
            dispatch_stripe_event(self.event)

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_webhooks.dispatch.logger.error")
    def test_dispatch_stripe_event_with_event_data_not_dict(self, mock_logger):
        self.event["data"] = ""

        with self.assertRaises(KeyError):
            dispatch_stripe_event(self.event)

        mock_logger.assert_called_once()

    @patch("apps.payments.services.stripe_webhooks.dispatch.logger.error")
    def test_dispatch_stripe_event_with_event_data_object_empty(self, mock_logger):
        self.event["data"]["object"] = {}

        with self.assertRaises(KeyError):
            dispatch_stripe_event(self.event)

        mock_logger.assert_called_once()
