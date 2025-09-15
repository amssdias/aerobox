from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.plan_factory import (
    PlanProFactory,
    PlaEnterpriseFactory,
)
from apps.subscriptions.factories.subscription import SubscriptionEnterprisePlanFactory
from apps.subscriptions.models.plan import Plan
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class TestSubscriptionViewSetChangePlan(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.other_user = UserFactory()

        cls.token, _ = Token.objects.get_or_create(user=cls.user)

        cls.plan_free = Plan.objects.get(is_free=True)
        cls.plan_pro = PlanProFactory(stripe_price_id="test_stripe_123")
        cls.plan_enterprise = PlaEnterpriseFactory()

        cls.subscription = SubscriptionEnterprisePlanFactory(
            user=cls.user,
            plan=cls.plan_enterprise,
        )

        cls.url = reverse(
            "subscriptions-change-plan", kwargs={"pk": cls.subscription.id}
        )
        cls.data = {
            "target_plan": cls.plan_pro.id,
        }

        cls.stripe_retrieve = MagicMock()
        cls.stripe_retrieve.id = "sub_123"
        cls.stripe_retrieve.__getitem__.side_effect = lambda k: {
            "items": {"data": [{"id": "si_abc123"}]}
        }[k]

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_change_plan_requires_authentication(self):
        self.client.logout()
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_plan_non_owner_forbidden(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(
            "No Subscription matches the given query.",
            str(response.data.get("detail", "")),
        )

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_from_free_to_pro(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        self.subscription.plan = self.plan_free
        self.subscription.save(update_fields=["plan"])

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Can't go lower than this subscription.", response.data.get("detail", "")
        )
        stripe_sub_retrieve.assert_not_called()
        stripe_sub_modify.assert_not_called()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_over_quota_blocks(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        file_size = self.plan_pro.max_storage_bytes + 100
        CloudFileFactory(user=self.user, size=file_size)

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("exceeds your new limit", response.data.get("detail", ""))
        stripe_sub_retrieve.assert_not_called()
        stripe_sub_modify.assert_not_called()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_paid_to_paid(self, stripe_sub_retrieve, stripe_sub_modify):
        stripe_sub_retrieve.return_value = self.stripe_retrieve

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "Your subscription is being updated to", response.data.get("detail", "")
        )

        stripe_sub_retrieve.assert_called_once_with(
            self.subscription.stripe_subscription_id
        )
        stripe_sub_modify.assert_called_once()

        _, kwargs = stripe_sub_modify.call_args
        self.assertEqual(kwargs.get("proration_behavior"), "create_prorations")
        self.assertEqual(kwargs.get("billing_cycle_anchor"), "unchanged")
        self.assertEqual(kwargs.get("payment_behavior"), "allow_incomplete")

        items = kwargs.get("items")
        self.assertIsInstance(items, list)
        self.assertEqual(items[0]["id"], "si_abc123")
        self.assertEqual(items[0]["price"], self.plan_pro.stripe_price_id)

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_paid_to_free(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        CloudFileFactory(user=self.user, size=12)
        stripe_sub_retrieve.return_value = self.stripe_retrieve

        response = self.client.post(
            self.url, {"target_plan": self.plan_free.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "Your subscription is being updated to", response.data.get("detail", "")
        )

        stripe_sub_retrieve.assert_called_once_with(
            self.subscription.stripe_subscription_id
        )
        stripe_sub_modify.assert_called_once_with(
            self.stripe_retrieve.id,
            cancel_at_period_end=True,
        )

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_equal_to_limit_allows_change(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        limit_bytes = self.plan_pro.max_storage_bytes
        CloudFileFactory(user=self.user, size=limit_bytes)

        stripe_sub_retrieve.return_value = self.stripe_retrieve

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        stripe_sub_retrieve.assert_called_once_with(
            self.subscription.stripe_subscription_id
        )
        stripe_sub_modify.assert_called_once()

        _, kwargs = stripe_sub_modify.call_args
        self.assertEqual(
            kwargs["items"][0]["id"],
            self.stripe_retrieve["items"].get("data")[0].get("id"),
        )
        self.assertEqual(kwargs["items"][0]["price"], self.plan_pro.stripe_price_id)

    # 8) No enforced limit (limit_bytes is None) → always allowed → Stripe modify called
    @patch("stripe.Subscription.modify")
    @patch("subscriptions.views.stripe.Subscription.retrieve")
    def _test_change_plan_with_no_enforced_limit_allows_change(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        # Create a target plan that yields max_storage_bytes = None (e.g., no metadata key)
        target_no_limit = PlanProFactory(
            name={"en": "Unlimited"},
            is_free=False,
            stripe_price_id="price_unlimited_999",
            metadata={},  # ensure your Plan.max_storage_bytes returns None here
        )
        # Even with huge usage, it should not block
        CloudFileFactory(user=self.owner, size=50 * 1024 * 1024 * 1024)  # 50 GB

        # stripe_sub_retrieve.return_value = ObjDict(
        #     id="sub_123",
        #     items={"data": [{"id": "si_ul"}]}
        # )

        self.client.force_authenticate(user=self.owner)
        resp = self.client.post(
            self.url, {"target_plan": target_no_limit.pk}, format="json"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("Unlimited", resp.data.get("detail", ""))
        self.assertIn("no enforced limit", resp.data.get("detail", ""))
        stripe_sub_retrieve.assert_called_once_with("sub_123")
        stripe_sub_modify.assert_called_once()
        _, kwargs = stripe_sub_modify.call_args
        self.assertEqual(kwargs["items"][0]["price"], target_no_limit.stripe_price_id)

    def test_change_plan_missing_target_plan_returns_400(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("target_plan" in k for k in response.data.keys()))

    def test_change_plan_on_canceled_subscription(self):
        self.subscription.status = SubscriptionStatusChoices.CANCELED.value
        self.subscription.save(update_fields=["status"])

        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_plan_on_inactive(self):
        self.subscription.status = SubscriptionStatusChoices.INACTIVE.value
        self.subscription.save(update_fields=["status"])

        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_plan_on_expired(self):
        self.subscription.status = SubscriptionStatusChoices.EXPIRED.value
        self.subscription.save(update_fields=["status"])

        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_plan_on_past_due(self):
        self.subscription.status = SubscriptionStatusChoices.PAST_DUE.value
        self.subscription.save(update_fields=["status"])

        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_plan_with_nonexistent_target_plan(self):
        non_existent_pk = 999999
        response = self.client.post(
            self.url, {"target_plan": non_existent_pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("target_plan" in k for k in response.data.keys()))

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_uses_first_stripe_item_when_multiple(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        s_retrieve = MagicMock()
        s_retrieve.id = "sub_123"
        s_retrieve.__getitem__.side_effect = lambda k: {
            "items": {"data": [{"id": "si_first"}, {"id": "si_second"}]}
        }[k]

        stripe_sub_retrieve.return_value = s_retrieve

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stripe_sub_retrieve.assert_called_once_with(
            self.subscription.stripe_subscription_id
        )
        stripe_sub_modify.assert_called_once()
        _, kwargs = stripe_sub_modify.call_args
        self.assertEqual(
            kwargs["items"][0]["id"], s_retrieve["items"].get("data")[0].get("id")
        )
        self.assertEqual(kwargs["items"][0]["price"], self.plan_pro.stripe_price_id)

    def test_change_plan_get_method_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @patch("stripe.Subscription.retrieve")
    def test_change_plan_to_free_with_over_quota(
            self, stripe_sub_retrieve
    ):
        over_free_limit_bytes = self.plan_free.max_storage_bytes + 1
        CloudFileFactory(user=self.user, size=over_free_limit_bytes)

        response = self.client.post(
            self.url, {"target_plan": self.plan_free.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("exceeds your new limit", response.data.get("detail", ""))
        stripe_sub_retrieve.assert_not_called()

    def test_change_plan_upgrade(self):
        self.subscription.plan = self.plan_pro
        self.subscription.save(update_fields=["plan"])
        CloudFileFactory(user=self.user, size=512 * 1024 * 1024)

        response = self.client.post(
            self.url, {"target_plan": self.plan_enterprise.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("target_plan" in k for k in response.data.keys()))

    def test_change_plan_same_plan(self):
        response = self.client.post(
            self.url, {"target_plan": self.plan_enterprise.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any("target_plan" in k for k in response.data.keys()))

    def test_change_plan_target_paid_without_stripe_price_id_returns_400(self):
        self.plan_pro.stripe_price_id = None
        self.plan_pro.save(update_fields=["stripe_price_id"])

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.subscriptions.views.subscription.logger.error")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_stripe_retrieve_empty_items_causes_500(
            self, stripe_sub_retrieve, mock_logger
    ):
        stripe_retrieve = MagicMock()
        stripe_retrieve.id = "sub_123"
        stripe_retrieve.__getitem__.side_effect = lambda k: {"items": {"data": []}}[k]
        stripe_sub_retrieve.return_value = stripe_retrieve

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        mock_logger.assert_called_once()

    @patch("apps.subscriptions.views.subscription.logger.error")
    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_stripe_modify_raises_error(
            self,
            stripe_sub_retrieve,
            stripe_sub_modify,
            mock_logger,
    ):
        stripe_sub_retrieve.return_value = self.stripe_retrieve
        stripe_sub_modify.side_effect = Exception("stripe blew up")

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("temporary issue", response.data.get("detail", "").lower())
        self.assertIn("try again later", response.data.get("detail", "").lower())
        mock_logger.assert_called_once()

    @patch("stripe.Subscription.retrieve")
    @patch("apps.subscriptions.views.subscription.logger.error")
    def test_change_plan_stripe_retrieve_raises_error(
            self, mock_logger, stripe_sub_retrieve
    ):
        stripe_sub_retrieve.side_effect = Exception("stripe down")

        response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("temporary issue", response.data.get("detail", "").lower())
        self.assertIn("try again later", response.data.get("detail", "").lower())
        mock_logger.assert_called_once()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    @patch("apps.subscriptions.views.subscription.logger.error")
    def test_change_plan_to_free_stripe_delete_raises_error(
            self, mock_logger, stripe_sub_retrieve, stripe_sub_modify
    ):
        stripe_sub_retrieve.return_value = self.stripe_retrieve
        stripe_sub_modify.side_effect = Exception("delete failed")

        response = self.client.post(
            self.url, {"target_plan": self.plan_free.pk}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("temporary issue", response.data.get("detail", "").lower())
        self.assertIn("try again later", response.data.get("detail", "").lower())
        mock_logger.assert_called_once()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_stripe_items_missing_key(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        stripe_retrieve = MagicMock()
        stripe_retrieve.id = "sub_123"
        stripe_retrieve.__getitem__.side_effect = lambda k: {"ite": None}[k]
        stripe_sub_retrieve.return_value = stripe_retrieve

        resp = self.client.post(self.url, self.data, format="json")

        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("temporary issue", resp.data.get("detail", "").lower())
        stripe_sub_modify.assert_not_called()

    @patch("stripe.Subscription.modify")
    @patch("stripe.Subscription.retrieve")
    def test_change_plan_stripe_items_wrong_type(
            self, stripe_sub_retrieve, stripe_sub_modify
    ):
        stripe_retrieve = MagicMock()
        stripe_retrieve.id = "sub_123"
        stripe_retrieve.__getitem__.side_effect = lambda k: {"items": None}[k]
        stripe_sub_retrieve.return_value = stripe_retrieve

        resp = self.client.post(self.url, self.data, format="json")

        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("temporary issue", resp.data.get("detail", "").lower())
        stripe_sub_modify.assert_not_called()
