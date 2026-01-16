from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.cloud_storage.exceptions import (
    FolderSharingNotAllowed,
    ShareLinkLimitReached,
    ShareLinkPasswordNotAllowed,
    ShareLinkExpirationTooLong,
)
from apps.cloud_storage.tests.factories.share_link_factory import ShareLinkFactory
from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.subscriptions.choices.subscription_choices import SubscriptionStatusChoices
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.subscriptions.models import Subscription, Plan
from apps.users.factories.user_factory import UserFactory


class UserModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser", email="test@example.com")
        cls.sub = SubscriptionFreePlanFactory(
            user=cls.user,
            status=SubscriptionStatusChoices.ACTIVE.value,
        )
        cls.feature = cls.sub.plan.plan_features.get(
            feature__code=FeatureCodeChoices.FILE_SHARING
        )
        cls.feature.feature.metadata = {}
        cls.feature.feature.save(update_fields=["metadata"])

    def test_active_subscription_returns_first_active_subscription(self):
        SubscriptionFreePlanFactory(
            user=self.user,
            status=SubscriptionStatusChoices.CANCELED.value,
        )

        SubscriptionFreePlanFactory(
            user=self.user,
            status=SubscriptionStatusChoices.INACTIVE.value,
        )

        SubscriptionFreePlanFactory(
            user=self.user,
            status=SubscriptionStatusChoices.EXPIRED.value,
        )

        self.assertEqual(self.user.active_subscription.id, self.sub.id)

    def test_active_subscription_returns_none_when_no_active_subscription(self):
        Subscription.objects.all().delete()

        SubscriptionFreePlanFactory(
            user=self.user,
            status=SubscriptionStatusChoices.CANCELED.value,
        )

        self.assertIsNone(self.user.active_subscription)

    def test_plan_returns_plan_of_active_subscription(self):
        self.assertEqual(self.user.plan.id, self.sub.plan.id)

    def test_file_sharing_config_returns_empty_dict_without_plan(self):
        Plan.objects.all().delete()
        self.assertIsNone(self.user.plan)
        self.assertEqual(self.user.file_sharing_config, {})

    def test_validate_create_or_update_sharelink_raises_when_folder_sharing_not_allowed(self):
        self.feature.metadata["allow_folder_sharing"] = False
        self.feature.save(update_fields=["metadata"])

        data = {
            "folders": [1, 2],
            "files": [],
            "expires_at": None,
            "password": None,
        }

        with self.assertRaises(FolderSharingNotAllowed):
            self.user.validate_create_or_update_sharelink(data)

    def test_file_sharing_config_returns_plan_config_when_plan_exists(self):
        self.assertIn("allow_folder_sharing", self.user.file_sharing_config)
        self.assertIn("allow_password", self.user.file_sharing_config)
        self.assertIn("max_active_links", self.user.file_sharing_config)
        self.assertIn("allow_choose_expiration", self.user.file_sharing_config)
        self.assertIn("max_expiration_minutes", self.user.file_sharing_config)
        self.assertIn("allow_custom_message", self.user.file_sharing_config)

    def test_active_share_links_returns_only_non_expired_links(self):
        now = timezone.now()

        expired = ShareLinkFactory(
            owner=self.user,
            expires_at=now - timedelta(hours=1),
        )

        no_expiration = ShareLinkFactory(
            owner=self.user,
            expires_at=None,
        )

        future_expiration = ShareLinkFactory(
            owner=self.user,
            expires_at=now + timedelta(hours=1),
        )

        active_links = list(self.user.active_share_links)

        self.assertIn(no_expiration, active_links)
        self.assertIn(future_expiration, active_links)
        self.assertNotIn(expired, active_links)
        self.assertEqual(len(active_links), 2)

    def test_validate_create_or_update_sharelink_raises_when_max_active_links_reached(self):
        self.feature.metadata["max_active_links"] = 2
        self.feature.save(update_fields=["metadata"])

        # Create 2 active links (reaching the limit)
        ShareLinkFactory(owner=self.user, expires_at=None)
        ShareLinkFactory(owner=self.user, expires_at=None)

        data = {
            "folders": [],
            "files": [2],
            "expires_at": None,
            "password": None,
        }

        with self.assertRaises(ShareLinkLimitReached):
            self.user.validate_create_or_update_sharelink(data)

    def test_validate_create_or_update_sharelink_raises_when_password_not_allowed(self):
        self.feature.metadata["allow_password"] = False
        self.feature.save(update_fields=["metadata"])

        data = {
            "folders": [],
            "files": [],
            "expires_at": None,
            "password": "secret123",
        }

        with self.assertRaises(ShareLinkPasswordNotAllowed):
            self.user.validate_create_or_update_sharelink(data)

    def test_validate_create_or_update_sharelink_raises_when_expiration_exceeds_explicit_max(
            self,
    ):
        self.feature.metadata["allow_choose_expiration"] = True
        self.feature.metadata["max_expiration_minutes"] = 30
        self.feature.save(update_fields=["metadata"])

        expires_at = timezone.now() + timedelta(minutes=45)

        data = {
            "folders": [],
            "files": [1],
            "expires_at": expires_at,
            "password": None,
        }

        with self.assertRaises(ShareLinkExpirationTooLong):
            self.user.validate_create_or_update_sharelink(data)

    def test_validate_create_or_update_sharelink_allows_any_expiration_when_max_is_null(self):
        self.feature.metadata["allow_choose_expiration"] = True
        self.feature.metadata["max_expiration_minutes"] = None
        self.feature.save(update_fields=["metadata"])

        expires_at = timezone.now() + timedelta(days=900)

        data = {
            "folders": [],
            "files": [],
            "expires_at": expires_at,
            "password": None,
        }

        result = self.user.validate_create_or_update_sharelink(data)
        self.assertTrue(result)

    @override_settings(DEFAULT_SHARELINK_EXPIRATION_MINUTES=60)
    def test_validate_create_or_update_sharelink_uses_default_max_when_key_missing(self):
        self.feature.metadata = {"allow_choose_expiration": True}
        self.feature.save(update_fields=["metadata"])

        expires_at = timezone.now() + timedelta(minutes=90)

        data = {
            "folders": [],
            "files": [],
            "expires_at": expires_at,
            "password": None,
        }

        with self.assertRaises(ShareLinkExpirationTooLong):
            self.user.validate_create_or_update_sharelink(data)

    def test_validate_create_or_update_sharelink_with_all_features_enabled(self):
        self.feature.metadata = {
            "allow_folder_sharing": True,
            "max_active_links": 5,
            "allow_password": True,
            "allow_choose_expiration": True,
            "max_expiration_minutes": 60,
        }
        self.feature.save(update_fields=["metadata"])

        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
        )

        expires_at = timezone.now() + timedelta(minutes=30)

        data = {
            "folders": [1, 2],
            "files": [10, 11],
            "expires_at": expires_at,
            "password": "strong-pass",
        }

        result = self.user.validate_create_or_update_sharelink(data)
        self.assertTrue(result)

    def test_validate_create_or_update_sharelink_with_unlimited_expiration(self):
        self.feature.metadata = {
            "allow_folder_sharing": True,
            "max_active_links": 5,
            "allow_password": True,
            "allow_choose_expiration": True,
            "max_expiration_minutes": None,
        }
        self.feature.save(update_fields=["metadata"])

        expires_at = timezone.now() + timedelta(days=365)

        data = {
            "folders": [],
            "files": [42],
            "expires_at": expires_at,
            "password": None,
        }

        result = self.user.validate_create_or_update_sharelink(data)
        self.assertTrue(result)

    def test_validate_create_or_update_sharelink_does_not_check_expiration_when_allow_choose_expiration_false(self):
        self.feature.metadata = {
            "allow_folder_sharing": True,
            "max_active_links": 5,
            "allow_password": True,
            "allow_choose_expiration": False,
            "max_expiration_minutes": 30,
        }
        self.feature.save(update_fields=["metadata"])

        expires_at = timezone.now() + timedelta(days=10)

        data = {
            "folders": [],
            "files": [1],
            "expires_at": expires_at,
            "password": None,
        }

        result = self.user.validate_create_or_update_sharelink(data)
        self.assertTrue(result)

    def test_validate_create_or_update_sharelink_does_not_check_when_expires_at_is_none(self):
        self.feature.metadata = {
            "allow_folder_sharing": True,
            "max_active_links": 5,
            "allow_password": True,
            "allow_choose_expiration": True,
            "max_expiration_minutes": 30,
        }
        self.feature.save(update_fields=["metadata"])

        data = {
            "folders": [],
            "files": [1],
            "expires_at": None,
            "password": None,
        }

        result = self.user.validate_create_or_update_sharelink(data)
        self.assertTrue(result)

    def test_validate_create_or_update_sharelink_uses_default_max_active_links_of_one(self):
        self.feature.metadata = {
            "allow_folder_sharing": True,
            "allow_password": True,
            "allow_choose_expiration": True,
            "max_expiration_minutes": None,
        }
        self.feature.save(update_fields=["metadata"])

        # First active link -> OK
        ShareLinkFactory(
            owner=self.user,
            expires_at=None,
        )

        data = {
            "folders": [],
            "files": [1],
            "expires_at": None,
            "password": None,
        }

        with self.assertRaises(ShareLinkLimitReached):
            self.user.validate_create_or_update_sharelink(data)
