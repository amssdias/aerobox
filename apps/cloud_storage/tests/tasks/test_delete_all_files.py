from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now

from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.tasks.delete_files import clear_all_deleted_files_from_user, delete_old_files
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory, SubscriptionProPlanFactory
from apps.subscriptions.models import Subscription
from apps.users.factories.user_factory import UserFactory

User = get_user_model()


class DeleteAllFilesFromUserTaskTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")

    def setUp(self):
        self.deleted_files = [
            CloudFileFactory(
                user=self.user,
                s3_key=f"test/file_{i}.txt",
                deleted_at=now()
            )
            for i in range(3)
        ]

    @patch.object(S3Service, "delete_file_from_s3")
    def test_all_deleted_files_are_removed_from_db_and_s3(self, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertEqual(mock_delete_s3.call_count, 3)
        self.assertEqual(CloudFile.deleted.filter(user=self.user).count(), 0)

    @patch.object(S3Service, "delete_file_from_s3")
    def test_no_deleted_files_nothing_happens(self, mock_delete_s3):
        user = UserFactory()
        clear_all_deleted_files_from_user(user.id)

        mock_delete_s3.assert_not_called()

    @patch.object(S3Service, "delete_file_from_s3")
    def test_only_soft_deleted_files_are_processed(self, mock_delete_s3):
        CloudFileFactory(user=self.user, s3_key="active.txt")
        clear_all_deleted_files_from_user(self.user.id)

        self.assertEqual(mock_delete_s3.call_count, 3)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=Exception("S3 error"))
    def test_files_with_failed_s3_deletion_are_not_removed_from_db(self, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertEqual(CloudFile.deleted.filter(user=self.user).count(), 3)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=Exception("S3 error"))
    @patch("apps.cloud_storage.tasks.delete_files.logger.error")
    def test_logs_error_when_s3_deletion_fails(self, mock_logger, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertTrue(mock_logger.called)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("apps.cloud_storage.tasks.delete_files.logger.info")
    def test_logs_info_when_files_deleted_successfully(self, mock_logger, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertTrue(mock_logger.called)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=[None, Exception("fail"), None])
    @patch("apps.cloud_storage.tasks.delete_files.logger.warning")
    def test_logs_warning_when_some_s3_deletions_fail(self, mock_logger, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertTrue(mock_logger.called)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=[None, Exception("fail"), None])
    def test_partial_s3_failures_only_successful_files_deleted(self, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertEqual(CloudFile.deleted.filter(user=self.user).count(), 1)

    @patch.object(S3Service, "delete_file_from_s3")
    def test_s3_service_delete_called_once_per_file(self, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertEqual(mock_delete_s3.call_count, 3)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("django.db.transaction.atomic")
    def test_transaction_atomicity_for_successful_deletions(self, mock_atomic, mock_delete_s3):
        clear_all_deleted_files_from_user(self.user.id)

        self.assertTrue(mock_atomic.called)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("apps.cloud_storage.tasks.delete_files.logger.info")
    def test_file_older_than_threshold_is_deleted(self, mock_logger, mock_delete_s3):
        file = CloudFileFactory(
            user=self.user,
            s3_key="test/deleted-file.txt",
            deleted_at=now() - timedelta(days=31),
        )

        clear_all_deleted_files_from_user(self.user.id, older_than_days=30)

        self.assertFalse(CloudFile.objects.filter(id=file.id).exists())
        mock_delete_s3.assert_called_once_with(object_name=file.s3_key)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("apps.cloud_storage.tasks.delete_files.logger.info")
    def test_file_newer_than_threshold_is_not_deleted(self, mock_logger, mock_delete_s3):
        file = CloudFileFactory(
            user=self.user,
            s3_key="test/file2-deleted.txt",
            deleted_at=now() - timedelta(days=10),
        )

        clear_all_deleted_files_from_user(self.user.id, older_than_days=30)

        self.assertTrue(CloudFile.objects.filter(id=file.id).exists())
        mock_delete_s3.assert_not_called()

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("apps.cloud_storage.tasks.delete_files.logger.info")
    def test_only_files_older_than_threshold_are_deleted(self, mock_logger, mock_delete_s3):
        old_file = CloudFileFactory(
            user=self.user,
            s3_key="test/old.txt",
            deleted_at=now() - timedelta(days=40),
        )
        recent_file = CloudFileFactory(
            user=self.user,
            s3_key="test/recent.txt",
            deleted_at=now() - timedelta(days=5),
        )

        clear_all_deleted_files_from_user(self.user.id, older_than_days=30)

        self.assertFalse(CloudFile.objects.filter(id=old_file.id).exists())
        self.assertTrue(CloudFile.objects.filter(id=recent_file.id).exists())
        mock_delete_s3.assert_called_once_with(object_name=old_file.s3_key)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("apps.cloud_storage.tasks.delete_files.logger.info")
    def test_older_than_days_is_none_deletes_all_deleted_files(self, mock_logger, mock_delete_s3):
        old_file = CloudFileFactory(
            user=self.user,
            s3_key="test/old.txt",
            deleted_at=now() - timedelta(days=50),
        )
        recent_file = CloudFileFactory(
            user=self.user,
            s3_key="test/recent.txt",
            deleted_at=now() - timedelta(days=5),
        )

        count_user_files = CloudFile.objects.filter(user=self.user).count()

        clear_all_deleted_files_from_user(self.user.id, older_than_days=None)

        self.assertFalse(CloudFile.objects.filter(id=old_file.id).exists())
        self.assertFalse(CloudFile.objects.filter(id=recent_file.id).exists())
        self.assertEqual(mock_delete_s3.call_count, count_user_files)


class DeleteOldFilesTaskUnitTests(TestCase):
    def setUp(self):
        self.user1 = UserFactory(username="user1")
        self.user2 = UserFactory(username="user2")
        self.free_plan = SubscriptionFreePlanFactory(user=self.user1)
        self.paid_plan = SubscriptionProPlanFactory(user=self.user2)

    @patch.object(S3Service, "delete_file_from_s3")
    def test_deletes_old_files(self, mock_delete_s3):
        CloudFileFactory(
            user=self.user1,
            s3_key="test/old.txt",
            deleted_at=now() - timedelta(days=50),
        )
        CloudFileFactory(
            user=self.user1,
            s3_key="test/recent.txt",
            deleted_at=now() - timedelta(days=5),
        )
        delete_old_files()

        self.assertEqual(CloudFile.objects.filter(user=self.user1).count(), 1)

    @patch.object(S3Service, "delete_file_from_s3")
    def test_deletes_old_files_from_free_sub_users(self, mock_delete_s3):
        CloudFileFactory(
            user=self.user1,
            s3_key="test/user1.txt",
            deleted_at=now() - timedelta(days=50),
        )
        CloudFileFactory(
            user=self.user1,
            s3_key="test/recent-user1.txt",
            deleted_at=now() - timedelta(days=5),
        )

        CloudFileFactory(
            user=self.user2,
            s3_key="test/old-user2.txt",
            deleted_at=now() - timedelta(days=50),
        )
        CloudFileFactory(
            user=self.user2,
            s3_key="test/recent-user2.txt",
            deleted_at=now() - timedelta(days=5),
        )

        delete_old_files()

        self.assertEqual(CloudFile.objects.filter(user=self.user1).count(), 1)
        self.assertEqual(CloudFile.objects.filter(user=self.user2).count(), 2)

    @patch("apps.cloud_storage.tasks.delete_files.group")
    def test_dispatches_task_for_only_free_active_users(self, mock_group):
        delete_old_files()

        mock_group.assert_called_once()

    @patch("apps.cloud_storage.tasks.delete_files.logger.info")
    @patch("apps.cloud_storage.tasks.delete_files.group")
    def test_logs_user_ids_and_count(self, mock_group, mock_logger):
        delete_old_files()
        mock_logger.assert_called()

        log_call_args = mock_logger.call_args[0][1]
        self.assertIn(self.user1.id, mock_logger.call_args[1]["extra"]["user_ids"])
        self.assertEqual(log_call_args, 1)

    @patch("apps.cloud_storage.tasks.delete_files.group")
    def test_calls_apply_async_once(self, mock_group):
        mock_job = MagicMock()
        mock_group.return_value = mock_job

        delete_old_files()
        mock_job.apply_async.assert_called_once()

    @patch("apps.cloud_storage.tasks.delete_files.group")
    @patch("apps.cloud_storage.tasks.delete_files.clear_all_deleted_files_from_user")
    def test_no_free_active_users_means_no_tasks(self, mock_task, mock_group):
        Subscription.objects.all().delete()
        delete_old_files()

        mock_task.assert_not_called()
        mock_group.assert_called_once()

    @patch("apps.cloud_storage.tasks.delete_files.group")
    @patch("apps.cloud_storage.tasks.delete_files.clear_all_deleted_files_from_user")
    def test_task_called_with_30_day_threshold(self, mock_task, mock_group):
        mock_task.s.return_value = MagicMock()
        delete_old_files()

        mock_task.s.assert_called_once_with(self.user1.id, 30)
        mock_group.assert_called_once()
