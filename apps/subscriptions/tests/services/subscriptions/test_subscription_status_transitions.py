from datetime import date
from unittest.mock import patch

from django.test import TestCase

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.models import Subscription
from apps.subscriptions.services.subscriptions.status_transitions import (
    update_cancel_subscription_status,
    activate_subscription,
    set_subscription_inactive,
    update_subscription_status_past_due,
)


class SubscriptionStatusTransitionTests(TestCase):

    def test_update_cancel_subscription_status_sets_canceled_and_end_date(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.ACTIVE.value, end_date=None)
        ended_at = date(2026, 2, 19)

        update_cancel_subscription_status(sub, ended_at)

        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatusChoices.CANCELED.value)
        self.assertEqual(sub.end_date, ended_at)

    def test_activate_subscription_updates_status_when_not_active(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.INACTIVE.value)

        activate_subscription(sub)

        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatusChoices.ACTIVE.value)

    def test_activate_subscription_does_not_save_when_already_active(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.ACTIVE.value)

        with patch.object(Subscription, "save") as mock_save:
            activate_subscription(sub)

        mock_save.assert_not_called()

    def test_set_subscription_inactive_updates_status_when_not_inactive(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.ACTIVE.value)

        set_subscription_inactive(sub)

        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatusChoices.INACTIVE.value)

    def test_set_subscription_inactive_does_not_save_when_already_inactive(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.INACTIVE.value)

        with patch.object(Subscription, "save") as mock_save:
            set_subscription_inactive(sub)

        mock_save.assert_not_called()

    def test_update_subscription_status_past_due_updates_when_not_past_due_or_canceled(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.ACTIVE.value)

        update_subscription_status_past_due(sub)

        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatusChoices.PAST_DUE.value)

    def test_update_subscription_status_past_due_does_not_save_when_already_past_due(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.PAST_DUE.value)

        with patch.object(Subscription, "save") as mock_save:
            update_subscription_status_past_due(sub)

        mock_save.assert_not_called()

    def test_update_subscription_status_past_due_does_not_update_when_canceled(self):
        sub = SubscriptionFactory(status=SubscriptionStatusChoices.CANCELED.value)

        update_subscription_status_past_due(sub)

        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatusChoices.CANCELED.value)
