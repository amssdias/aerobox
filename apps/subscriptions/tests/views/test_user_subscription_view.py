from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.serializers.subscription import SubscriptionSerializer
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class UserSubscriptionViewTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")
        cls.url = reverse('user-subscription')

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_user_gets_401(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.subscriptions.views.user_subscription.logger.warning")
    def test_no_active_subscription_returns_404(self, mock_logger):
        SubscriptionFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_logger.assert_called_once()

    def test_single_active_subscription_returns_subscription(self):
        subscription = SubscriptionFactory(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, SubscriptionSerializer(subscription).data)

    @patch("apps.subscriptions.views.user_subscription.logger.error")
    def test_multiple_active_subscriptions_return_400(self, mock_logger):
        SubscriptionFactory(user=self.user, status=SubscriptionStatusChoices.ACTIVE.value)
        SubscriptionFactory(user=self.user, status=SubscriptionStatusChoices.ACTIVE.value)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_logger.assert_called_once()

    @patch("apps.subscriptions.views.user_subscription.logger.warning")
    def test_inactive_subscription_ignored(self, mock_logger):
        SubscriptionFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_logger.assert_called_once()

    def test_mixed_status_subscriptions_only_active_matters(self):
        SubscriptionFactory(user=self.user, status=SubscriptionStatusChoices.INACTIVE.value)
        active = SubscriptionFactory(user=self.user, status=SubscriptionStatusChoices.ACTIVE.value)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, SubscriptionSerializer(active).data)

    @patch("apps.subscriptions.views.user_subscription.logger.warning")
    def test_expired_subscription_ignored(self, mock_logger):
        SubscriptionFactory(user=self.user, status=SubscriptionStatusChoices.EXPIRED.value)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_logger.assert_called_once()

    @patch("apps.subscriptions.views.user_subscription.logger.warning")
    def test_canceled_subscription_ignored(self, mock_logger):
        SubscriptionFactory(user=self.user, status=SubscriptionStatusChoices.CANCELED.value)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_logger.assert_called_once()

    def test_subscription_for_different_user_not_returned(self):
        other_user = UserFactory()
        SubscriptionFactory(user=other_user, status=SubscriptionStatusChoices.ACTIVE.value)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_only_allows_get_method(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
