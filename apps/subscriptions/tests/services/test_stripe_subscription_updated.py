from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.subscriptions.factories.plan_factory import PlaEnterpriseFactory, PlanProFactory
from apps.subscriptions.factories.subscription import SubscriptionEnterprisePlanFactory
from apps.subscriptions.models import Plan
from apps.subscriptions.services.stripe_events.stripe_subscription_updated import SubscriptionUpdatedHandler
from apps.users.factories.user_factory import UserFactory


class SubscriptionUpdatedHandlerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")
        cls.subscription = SubscriptionEnterprisePlanFactory(
            user=cls.user,
            stripe_subscription_id="sub_enterprise_test_123"
        )
        cls.pro_plan = PlanProFactory(stripe_price_id="1234")
        cls.enterprise_plan = PlaEnterpriseFactory(stripe_price_id="enterprise_plan_123")

    def setUp(self):
        self.data = {
            "data": {
                "object": {
                    "id": "sub_enterprise_test_123"
                },
                "previous_attributes": {
                    "plan": {"id": self.enterprise_plan.stripe_price_id},
                }
            },
        }
        self.handler = SubscriptionUpdatedHandler(self.data)

    @patch.object(SubscriptionUpdatedHandler, "update_subscription")
    def test_process_calls_update_subscription_with_ids(self, mock_update):
        self.handler.process()
        mock_update.assert_called_once_with(
            self.data.get("data").get("object").get("id"),
            {"plan": {"id": self.enterprise_plan.stripe_price_id}}
        )

    @patch.object(SubscriptionUpdatedHandler, "change_plan_subscription")
    @patch("stripe.Subscription.retrieve")
    @patch.object(SubscriptionUpdatedHandler, "get_subscription")
    def test_update_subscription_no_previous_plan_does_nothing(self, mock_get_sub, mock_stripe_sub_retrieve,
                                                               mock_change):
        self.handler.update_subscription(subscription_id="sub_123", previous_attributes={})

        mock_get_sub.assert_called_once()
        mock_stripe_sub_retrieve.assert_called_once()
        mock_change.assert_not_called()

    @patch.object(SubscriptionUpdatedHandler, "change_plan_subscription")
    @patch("stripe.Subscription.retrieve")
    def test_update_subscription_triggers_change_when_previous_plan_matches_current(self, mock_stripe_sub_retrieve,
                                                                                    mock_change):
        self.handler.process()
        mock_stripe_sub_retrieve.return_value = None

        mock_stripe_sub_retrieve.assert_called_once()
        mock_change.assert_called_once()

    @patch("stripe.Subscription.retrieve")
    def test_change_plan_subscription_successfully(self, mock_stripe_sub_retrieve):
        self.assertEqual(self.subscription.plan.id, self.enterprise_plan.id)
        mock_stripe_sub_retrieve.return_value = MagicMock(plan={"id": self.pro_plan.stripe_price_id},
                                                          cancel_at_period_end=False)

        self.handler.process()

        self.subscription.refresh_from_db()
        self.assertTrue(self.subscription.is_recurring)
        self.assertEqual(self.subscription.plan_id, self.pro_plan.id)

    @patch("stripe.Subscription.retrieve")
    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_updated.logger.critical")
    def test_change_plan_subscription_no_plan_found(self, mock_logger, mock_stripe_sub_retrieve):
        self.assertEqual(self.subscription.plan.id, self.enterprise_plan.id)
        mock_stripe_sub_retrieve.return_value = MagicMock(plan={"id": "not_plan"})

        self.handler.process()

        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.plan_id, self.enterprise_plan.id)
        mock_logger.assert_called_once()

    @patch.object(SubscriptionUpdatedHandler, "change_plan_subscription")
    def test_update_subscription_previous_plan_differs_from_current(self, mock_change):
        self.subscription.plan = self.pro_plan
        self.subscription.save(update_fields=["plan"])

        self.handler.process()

        mock_change.assert_not_called()

    def test_get_plan_ignores_free_plans(self):
        result = self.handler.get_plan(None)
        self.assertIsNone(result)

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_updated.logger.critical")
    def test_get_plan_logs_critical_when_not_found(self, mock_logger):
        result = self.handler.get_plan("price_missing")

        self.assertIsNone(result)
        mock_logger.assert_called_once()

    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_updated.Plan.objects.get")
    @patch("apps.subscriptions.services.stripe_events.stripe_subscription_updated.logger.critical")
    def test_get_plan_logs_critical_when_multiple_objects_returned(self, mock_logger, mock_get):
        mock_get.side_effect = Plan.MultipleObjectsReturned

        result = self.handler.get_plan("price_dup")
        self.assertIsNone(result)
        mock_logger.assert_called_once()

    @patch.object(SubscriptionUpdatedHandler, "change_plan_subscription")
    @patch("stripe.Subscription.retrieve")
    def test_update_subscription_handles_none_subscription_safely(self, mock_stripe_sub_retrieve, mock_change):
        self.handler.update_subscription(
            subscription_id="non_existing",
            previous_attributes={"plan": {"id": self.enterprise_plan.stripe_price_id}},
        )
        mock_stripe_sub_retrieve.return_value = False

        mock_change.assert_not_called()
        mock_stripe_sub_retrieve.assert_not_called()

    @patch("stripe.Subscription.retrieve")
    def test_cancel_subscription_successfully(self, mock_stripe_sub_retrieve):
        self.assertTrue(self.subscription.is_recurring)
        mock_stripe_sub_retrieve.return_value = MagicMock(cancel_at_period_end=True)

        self.handler.update_subscription(
            subscription_id=self.subscription.stripe_subscription_id,
            previous_attributes={},
        )

        self.subscription.refresh_from_db()
        self.assertFalse(self.subscription.is_recurring)
