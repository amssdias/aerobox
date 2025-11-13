from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import now

from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED
from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.utils.size_utils import mb_to_human_gb, get_user_used_bytes
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class CloudStorageUtilsTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser", password="testpass")
        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)
        cls.plan = cls.subscription.plan

    # --------------------------------
    # --- Tests for mb_to_human_gb ---
    # --------------------------------

    def test_mb_to_human_gb_with_valid_values(self):
        self.assertEqual(mb_to_human_gb(5000), "5.0 GB")
        self.assertEqual(mb_to_human_gb(1536), "1.536 GB")

    def test_mb_to_human_gb_with_none_value(self):
        self.assertEqual(mb_to_human_gb(None), "0.0 GB")

    def test_mb_to_human_gb_with_zero(self):
        self.assertEqual(mb_to_human_gb(0), "0.0 GB")

    # -------------------------------------
    # --- Tests for get_user_used_bytes ---
    # -------------------------------------

    def test_get_user_used_bytes_no_files(self):
        used_bytes = get_user_used_bytes(self.user)
        self.assertEqual(used_bytes, 0)

    def test_get_user_used_bytes_with_files(self):
        CloudFileFactory(
            user=self.user,
            file_name="file2.txt",
            path="file1.txt",
            status=SUCCESS,
            size=1000,
        )
        CloudFileFactory(
            user=self.user,
            file_name="file1.txt",
            path="file2.txt",
            status=SUCCESS,
            size=5000,
        )
        CloudFileFactory(
            user=self.user,
            file_name="file3.txt",
            path="file3.txt",
            status=FAILED,
            size=1000,
        )
        CloudFileFactory(
            user=self.user,
            file_name="file4.txt",
            path="file4.txt",
            deleted_at=now() - timedelta(days=31),
            status=SUCCESS,
            size=1000,
        )

        used_bytes = get_user_used_bytes(self.user)
        self.assertEqual(used_bytes, 6000)
