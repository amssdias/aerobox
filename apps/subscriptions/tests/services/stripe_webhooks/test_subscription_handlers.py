from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.subscriptions.services.stripe_webhooks.handlers.common import build_subscription_summary
from apps.subscriptions.services.stripe_webhooks.handlers.subscription import (
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
)


class TestSubscriptionWebhookHandlers(SimpleTestCase):
    @patch(
        "apps.subscriptions.services.stripe_webhooks.handlers.subscription.create_subscription"
    )
    @patch(
        "apps.subscriptions.services.stripe_webhooks.handlers.subscription.build_subscription_summary"
    )
    def test_handle_subscription_created_builds_summary_and_creates_subscription(
            self,
            build_subscription_summary,
            create_subscription,
    ):
        event = {"id": "evt_123", "type": "customer.subscription.created"}
        subscription_summary = Mock(name="subscription_summary")
        build_subscription_summary.return_value = subscription_summary

        handle_subscription_created(event)

        build_subscription_summary.assert_called_once_with(event)
        create_subscription.assert_called_once_with(subscription_summary)

    @patch(
        "apps.subscriptions.services.stripe_webhooks.handlers.subscription.update_subscription"
    )
    @patch(
        "apps.subscriptions.services.stripe_webhooks.handlers.subscription.build_subscription_summary"
    )
    def test_handle_subscription_updated_builds_summary_and_updates_subscription(
            self,
            build_subscription_summary,
            update_subscription,
    ):
        event = {"id": "evt_456", "type": "customer.subscription.updated"}
        subscription_summary = Mock(name="subscription_summary")
        build_subscription_summary.return_value = subscription_summary

        handle_subscription_updated(event)

        build_subscription_summary.assert_called_once_with(event)
        update_subscription.assert_called_once_with(subscription_summary)

    @patch(
        "apps.subscriptions.services.stripe_webhooks.handlers.subscription.cancel_subscription"
    )
    @patch(
        "apps.subscriptions.services.stripe_webhooks.handlers.subscription.build_subscription_summary"
    )
    def test_handle_subscription_deleted_builds_summary_and_cancels_subscription(
            self,
            build_subscription_summary,
            cancel_subscription,
    ):
        event = {"id": "evt_789", "type": "customer.subscription.deleted"}
        subscription_summary = Mock(name="subscription_summary")
        build_subscription_summary.return_value = subscription_summary

        handle_subscription_deleted(event)

        build_subscription_summary.assert_called_once_with(event)
        cancel_subscription.assert_called_once_with(subscription_summary)


class TestBuildSubscriptionSummary(SimpleTestCase):

    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.to_subscription_summary")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.get_stripe_subscription")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_object_id")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_event_object")
    def test_build_subscription_summary_happy_path(
            self,
            require_event_object,
            require_object_id,
            get_stripe_subscription,
            to_subscription_summary,
    ):
        event = {"id": "evt_1"}

        obj = {"id": "sub_123"}
        subscription_id = "sub_123"
        stripe_sub = Mock(name="stripe_sub")
        expected_summary = Mock(name="subscription_summary")

        require_event_object.return_value = obj
        require_object_id.return_value = subscription_id
        get_stripe_subscription.return_value = stripe_sub
        to_subscription_summary.return_value = expected_summary

        result = build_subscription_summary(event)

        self.assertIs(result, expected_summary)
        require_event_object.assert_called_once_with(event)
        require_object_id.assert_called_once_with(obj, what="subscription")
        get_stripe_subscription.assert_called_once_with(subscription_id)
        to_subscription_summary.assert_called_once_with(stripe_sub)

    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_event_object")
    def test_build_subscription_summary_propagates_require_event_object_error(self, require_event_object):
        event = {"id": "evt_1"}
        require_event_object.side_effect = ValueError("missing object")

        with self.assertRaises(ValueError):
            build_subscription_summary(event)

    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_object_id")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_event_object")
    def test_build_subscription_summary_propagates_require_object_id_error(
            self,
            require_event_object,
            require_object_id,
    ):
        event = {"id": "evt_1"}
        obj = {"id": None}
        require_event_object.return_value = obj
        require_object_id.side_effect = ValueError("missing subscription id")

        with self.assertRaises(ValueError):
            build_subscription_summary(event)

    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.get_stripe_subscription")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_object_id")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_event_object")
    def test_build_subscription_summary_propagates_get_stripe_subscription_error(
            self,
            require_event_object,
            require_object_id,
            get_stripe_subscription,
    ):
        event = {"id": "evt_1"}
        require_event_object.return_value = {"id": "sub_123"}
        require_object_id.return_value = "sub_123"
        get_stripe_subscription.side_effect = RuntimeError("stripe down")

        with self.assertRaises(RuntimeError):
            build_subscription_summary(event)

    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.to_subscription_summary")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.get_stripe_subscription")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_object_id")
    @patch("apps.subscriptions.services.stripe_webhooks.handlers.common.require_event_object")
    def test_build_subscription_summary_propagates_to_subscription_summary_error(
            self,
            require_event_object,
            require_object_id,
            get_stripe_subscription,
            to_subscription_summary,
    ):
        event = {"id": "evt_1"}
        require_event_object.return_value = {"id": "sub_123"}
        require_object_id.return_value = "sub_123"
        get_stripe_subscription.return_value = Mock(name="stripe_sub")
        to_subscription_summary.side_effect = TypeError("bad stripe sub")

        with self.assertRaises(TypeError):
            build_subscription_summary(event)
