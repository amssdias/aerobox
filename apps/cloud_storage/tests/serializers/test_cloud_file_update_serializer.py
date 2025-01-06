from django.test import TestCase

from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED, PENDING
from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.serializers import CloudFileUpdateSerializer


class CloudFileUpdateSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.serializer = CloudFileUpdateSerializer
        cls.cloud_file = CloudFileFactory()

    def test_valid_update_status(self):
        data = {"status": SUCCESS}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_file = serializer.save()
        self.assertEqual(updated_file.status, SUCCESS)

    def test_valid_update_error_message(self):
        data = {"error_message": "Network issue"}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_file = serializer.save()
        self.assertEqual(updated_file.error_message, "Network issue")

    def test_update_both_fields(self):
        data = {"status": FAILED, "error_message": "Timeout error"}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_file = serializer.save()
        self.assertEqual(updated_file.status, FAILED)
        self.assertEqual(updated_file.error_message, "Timeout error")

    def test_empty_status(self):
        data = {"status": ""}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_empty_error_message(self):
        data = {"error_message": ""}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_status_type(self):
        data = {"status": 123}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_missing_status_field(self):
        data = {"error_message": "Some error"}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_error_message_field(self):
        data = {"status": PENDING}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_completely_empty_payload(self):
        data = {}
        serializer = self.serializer(instance=self.cloud_file, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
