from unittest.mock import patch

from django.test import TestCase
from django.utils.timezone import now

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.tasks.delete_all_files import delete_all_files_from_user
from apps.users.factories.user_factory import UserFactory


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
        delete_all_files_from_user(self.user.id)

        self.assertEqual(mock_delete_s3.call_count, 3)
        self.assertEqual(CloudFile.deleted.filter(user=self.user).count(), 0)

    @patch.object(S3Service, "delete_file_from_s3")
    def test_no_deleted_files_nothing_happens(self, mock_delete_s3):
        user = UserFactory()
        delete_all_files_from_user(user.id)

        mock_delete_s3.assert_not_called()

    @patch.object(S3Service, "delete_file_from_s3")
    def test_only_soft_deleted_files_are_processed(self, mock_delete_s3):
        CloudFileFactory(user=self.user, s3_key="active.txt")
        delete_all_files_from_user(self.user.id)

        self.assertEqual(mock_delete_s3.call_count, 3)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=Exception("S3 error"))
    def test_files_with_failed_s3_deletion_are_not_removed_from_db(self, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertEqual(CloudFile.deleted.filter(user=self.user).count(), 3)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=Exception("S3 error"))
    @patch("apps.cloud_storage.tasks.delete_all_files.logger.error")
    def test_logs_error_when_s3_deletion_fails(self, mock_logger, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertTrue(mock_logger.called)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("apps.cloud_storage.tasks.delete_all_files.logger.info")
    def test_logs_info_when_files_deleted_successfully(self, mock_logger, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertTrue(mock_logger.called)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=[None, Exception("fail"), None])
    @patch("apps.cloud_storage.tasks.delete_all_files.logger.warning")
    def test_logs_warning_when_some_s3_deletions_fail(self, mock_logger, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertTrue(mock_logger.called)

    @patch.object(S3Service, "delete_file_from_s3", side_effect=[None, Exception("fail"), None])
    def test_partial_s3_failures_only_successful_files_deleted(self, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertEqual(CloudFile.deleted.filter(user=self.user).count(), 1)

    @patch.object(S3Service, "delete_file_from_s3")
    def test_s3_service_delete_called_once_per_file(self, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertEqual(mock_delete_s3.call_count, 3)

    @patch.object(S3Service, "delete_file_from_s3")
    @patch("django.db.transaction.atomic")
    def test_transaction_atomicity_for_successful_deletions(self, mock_atomic, mock_delete_s3):
        delete_all_files_from_user(self.user.id)

        self.assertTrue(mock_atomic.called)
