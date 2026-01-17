from unittest.mock import Mock, patch

from django.test import TestCase

from apps.cloud_storage.choices.cloud_file_error_code_choices import CloudFileErrorCode
from apps.cloud_storage.constants.cloud_files import FAILED
from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.services.uploads.file_upload_finalizer_service import (
    FileUploadFinalizerService,
)
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.features.choices.feature_code_choices import FeatureCodeChoices
from apps.subscriptions.factories.subscription import SubscriptionFreePlanFactory
from apps.users.factories.user_factory import UserFactory


class FileUploadFinalizerServiceTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="testuser")
        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)
        cls.plan = cls.subscription.plan

    def setUp(self):
        self.cloud_file = CloudFileFactory(
            user=self.user,
            size=123,
            content_type="application/pdf",
            file_name="test.pdf",
            s3_key="user_1/test.pdf",
        )

    @patch.object(S3Service, "head", return_value=None)
    def test_finalize_marks_failed_when_sync_returns_none(self, mock_s3_head):
        storage = Mock(spec=S3Service)
        service = FileUploadFinalizerService(sync_service=None, storage=storage)

        result = service.finalize(self.cloud_file)

        self.assertFalse(result)

        self.cloud_file.refresh_from_db()

        self.assertEqual(self.cloud_file.status, FAILED)
        self.assertEqual(
            self.cloud_file.error_code,
            CloudFileErrorCode.FILE_NOT_FOUND_IN_S3.value,
        )
        self.assertEqual(
            self.cloud_file.error_message,
            "File not found in storage during upload verification.",
        )

        storage.delete_file.assert_not_called()

    @patch.object(S3Service, "head")
    def test_finalize_with_no_size_change_does_not_check_quota(self, mock_s3_head):
        mock_s3_head.return_value = {
            "size": self.cloud_file.size,
            "content_type": self.cloud_file.content_type
        }

        storage = Mock(spec=S3Service)
        service = FileUploadFinalizerService(sync_service=None, storage=storage)

        result = service.finalize(self.cloud_file)

        self.assertTrue(result)

        storage.delete_file.assert_not_called()
        self.cloud_file.refresh_from_db()
        self.assertIsNone(self.cloud_file.error_code)

    @patch.object(FileUploadFinalizerService, "is_over_quota", return_value=False)
    @patch.object(S3Service, "head")
    def test_finalize_size_changed_but_not_over_quota(self, mock_s3_head, mock_is_over_quota):
        mock_s3_head.return_value = {
            "size": self.cloud_file.size + 123,
            "content_type": self.cloud_file.content_type
        }

        storage = Mock(spec=S3Service)
        service = FileUploadFinalizerService(sync_service=None, storage=storage)

        result = service.finalize(self.cloud_file)

        self.assertTrue(result)
        mock_is_over_quota.assert_called_once_with(self.cloud_file)
        storage.delete_file.assert_not_called()

        self.cloud_file.refresh_from_db()
        self.assertIsNone(self.cloud_file.error_code)
        self.assertNotEqual(self.cloud_file.status, FAILED)

    @patch.object(S3Service, "head")
    @patch.object(S3Service, "delete_file")
    @patch.object(FileUploadFinalizerService, "is_over_quota", return_value=True)
    def test_finalize_size_changed_and_over_quota_marks_failed_and_deletes(
            self,
            mock_is_over_quota,
            mock_delete_file,
            mock_s3_head,
    ):
        mock_s3_head.return_value = {
            "size": self.cloud_file.size + 1,
            "content_type": self.cloud_file.content_type
        }

        service = FileUploadFinalizerService()

        result = service.finalize(self.cloud_file)

        self.assertFalse(result)
        mock_is_over_quota.assert_called_once_with(self.cloud_file)
        mock_delete_file.assert_called_once_with(self.cloud_file.s3_key)

        self.cloud_file.refresh_from_db()
        self.assertEqual(self.cloud_file.status, FAILED)
        self.assertEqual(
            self.cloud_file.error_code,
            CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value,
        )
        self.assertEqual(
            self.cloud_file.error_message,
            "User exceeded storage quota after final size verification.",
        )

    def test_mark_as_failed_sets_status_and_error_fields(self):
        FileUploadFinalizerService.mark_as_failed(
            self.cloud_file,
            error_code=CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value,
            error_message="Something went wrong.",
        )

        self.cloud_file.refresh_from_db()

        self.assertEqual(self.cloud_file.status, FAILED)
        self.assertEqual(self.cloud_file.error_code, CloudFileErrorCode.STORAGE_QUOTA_EXCEEDED.value)
        self.assertEqual(self.cloud_file.error_message, "Something went wrong.")

    @patch("apps.cloud_storage.services.uploads.file_upload_finalizer_service.get_user_used_bytes")
    def test_is_over_quota_returns_false_when_used_equals_limit(self, mock_used_bytes):
        plan = self.subscription.plan

        feature = plan.plan_features.get(feature__code=FeatureCodeChoices.CLOUD_STORAGE)
        feature.metadata["max_storage_mb"] = 10_000
        feature.save(update_fields=["metadata"])

        mock_used_bytes.return_value = 10_000 * 1000 * 1000

        result = FileUploadFinalizerService.is_over_quota(self.cloud_file)
        self.assertFalse(result)

    @patch("apps.cloud_storage.services.uploads.file_upload_finalizer_service.get_user_used_bytes")
    def test_is_over_quota_returns_true_when_used_greater_than_limit(self, mock_used_bytes):
        plan = self.subscription.plan

        feature = plan.plan_features.get(feature__code=FeatureCodeChoices.CLOUD_STORAGE)
        feature.metadata["max_storage_mb"] = 10_000
        feature.save(update_fields=["metadata"])

        mock_used_bytes.return_value = 10_001 * 1000 * 1000

        result = FileUploadFinalizerService.is_over_quota(self.cloud_file)
        self.assertTrue(result)

    @patch("apps.cloud_storage.services.uploads.file_upload_finalizer_service.get_user_used_bytes")
    def test_is_over_quota_returns_false_when_used_less_than_limit(self, mock_used_bytes):
        plan = self.subscription.plan

        feature = plan.plan_features.get(feature__code=FeatureCodeChoices.CLOUD_STORAGE)
        feature.metadata["max_storage_mb"] = 10_000
        feature.save(update_fields=["metadata"])

        mock_used_bytes.return_value = 9_999 * 1000 * 1000

        result = FileUploadFinalizerService.is_over_quota(self.cloud_file)
        self.assertFalse(result)
