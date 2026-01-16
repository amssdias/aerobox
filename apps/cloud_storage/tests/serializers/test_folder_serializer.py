from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.cloud_storage.models import Folder
from apps.cloud_storage.serializers import FolderParentSerializer
from apps.cloud_storage.serializers import FolderSerializer
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.subscriptions.factories.plan_factory import PlanFreeFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory, SubscriptionFreePlanFactory
from apps.subscriptions.models import Plan
from apps.users.factories.user_factory import UserFactory


class FolderParentSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="test-user")
        cls.folder = FolderFactory(name="Root Folder", user=cls.user)
        cls.serializer = FolderParentSerializer

    def test_serializes_id_and_name_only(self):
        serializer = self.serializer(instance=self.folder)
        data = serializer.data

        self.assertEqual(set(data.keys()), {"id", "name"})
        self.assertEqual(data["id"], self.folder.id)
        self.assertEqual(data["name"], "Root Folder")

    def test_does_not_include_unexpected_fields(self):
        serializer = self.serializer(instance=self.folder)
        data = serializer.data

        self.assertNotIn("user", data)
        self.assertNotIn("parent", data)
        self.assertNotIn("created_at", data)


class FolderSerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = UserFactory(email="test@example.com", password="pass123")
        cls.parent_folder = FolderFactory(name="Parent", user=cls.user)

        cls.plan = Plan.objects.get(is_free=True)
        cls.subscription = SubscriptionFreePlanFactory(user=cls.user)

        cls.serializer = FolderSerializer

    def get_context(self):
        request = self.factory.post("/fake-url/")
        request.user = self.user
        return {"request": request}

    def test_serializes_expected_fields(self):
        folder = FolderFactory(name="Child", parent=self.parent_folder, user=self.user)
        serializer = self.serializer(instance=folder, context=self.get_context())

        data = serializer.data

        self.assertEqual(set(data.keys()),
                         {"id", "name", "parent", "user", "created_at", "updated_at", "subfolders_count",
                          "files_count"})
        self.assertEqual(data["name"], "Child")
        self.assertEqual(data["parent"]["id"], self.parent_folder.id)

    def test_create_folder_without_parent(self):
        data = {"name": "Top Level Folder"}
        serializer = self.serializer(data=data, context=self.get_context())

        self.assertTrue(serializer.is_valid(), serializer.errors)

        folder = serializer.save()

        self.assertEqual(folder.name, "Top Level Folder")
        self.assertIsNone(folder.parent)
        self.assertEqual(folder.user, self.user)

    def test_create_folder_with_parent(self):
        data = {"name": "Sub Folder", "parent_id": self.parent_folder.id}
        serializer = self.serializer(data=data, context=self.get_context())

        self.assertTrue(serializer.is_valid(), serializer.errors)

        folder = serializer.save()

        self.assertEqual(folder.parent, self.parent_folder)

    def test_duplicate_name_in_same_parent_raises_error(self):
        FolderFactory(name="My Folder", user=self.user, parent=self.parent_folder)
        data = {"name": "My Folder", "parent_id": self.parent_folder.id}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "A folder with this name already exists"):
            serializer.is_valid(raise_exception=True)

    def test_duplicate_name_in_different_parent_is_allowed(self):
        other_folder = FolderFactory(name="Another", user=self.user)
        FolderFactory(name="Shared Name", user=self.user, parent=self.parent_folder)
        data = {"name": "Shared Name", "parent_id": other_folder.id}

        serializer = self.serializer(data=data, context=self.get_context())

        self.assertTrue(serializer.is_valid())

    def test_no_active_subscription_raises_error(self):
        self.subscription.status = "inactive"
        self.subscription.save()

        data = {"name": "Without Subscription"}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "need an active subscription"):
            serializer.is_valid(raise_exception=True)

    def test_missing_folder_creation_feature_raises_error(self):
        user = UserFactory(email="test@example.com", password="pass123")
        plan = PlanFreeFactory()
        SubscriptionFactory(
            user=user,
            plan=plan,
            status="active",
            end_date=timezone.now().date() + timedelta(days=30)
        )

        data = {"name": "Feature Missing"}
        request = self.factory.post("/fake-url/")
        request.user = user
        context = {"request": request}

        serializer = self.serializer(data=data, context=context)

        with self.assertRaisesRegex(ValidationError, "does not include the folder creation feature"):
            serializer.is_valid(raise_exception=True)

    def test_invalid_name_has_reverted_slash(self):
        data = {"name": "invalid\\path"}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path must use '/' instead of."):
            self.assertFalse(serializer.is_valid(raise_exception=True))
            self.assertIn("name", serializer.errors)

    def test_invalid_name_starting_with_slash(self):
        data = {"name": "/invalid/name"}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path cannot start or end with '/'."):
            serializer.is_valid(raise_exception=True)
            self.assertIn("name", serializer.errors)

    def test_invalid_name_ending_with_slash(self):
        data = {"name": "invalid/path/"}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path cannot start or end with '/'."):
            self.assertFalse(serializer.is_valid(raise_exception=True))
            self.assertIn("name", serializer.errors)

    def test_invalid_name_starting_and_ending_with_slash(self):
        data = {"name": "/invalid/path/"}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path cannot start or end with '/'."):
            self.assertFalse(serializer.is_valid(raise_exception=True))
            self.assertIn("name", serializer.errors)

    def test_invalid_name_duplicate_slash(self):
        data = {"name": "invalid//path"}
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path cannot contain consecutive slashes."):
            self.assertFalse(serializer.is_valid(raise_exception=True))
            self.assertIn("name", serializer.errors)

        data["name"] = "//invalid/path"
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path cannot start or end with '/'."):
            self.assertFalse(serializer.is_valid(raise_exception=True))
            self.assertIn("name", serializer.errors)

        data["name"] = "invalid/path//"
        serializer = self.serializer(data=data, context=self.get_context())

        with self.assertRaisesRegex(ValidationError, "The file path cannot start or end with '/'."):
            self.assertFalse(serializer.is_valid(raise_exception=True))
            self.assertIn("name", serializer.errors)

    @patch("apps.cloud_storage.serializers.folder_serializer.update_folder_file_paths_task.delay")
    def test_update_name_triggers_path_update(self, mock_task):
        serializer = self.serializer(
            instance=self.parent_folder,
            data={"name": "Renamed"},
            context=self.get_context(),
            partial=True
        )
        self.assertTrue(serializer.is_valid())
        folder = serializer.save()

        self.assertEqual(folder.name, "Renamed")
        mock_task.assert_called_once_with(folder.id)

    @patch("apps.cloud_storage.serializers.folder_serializer.update_folder_file_paths_task.delay")
    def test_update_parent_triggers_path_update(self, mock_task):
        new_parent = FolderFactory(name="NewParent", user=self.user)
        serializer = self.serializer(
            instance=self.parent_folder,
            data={"parent_id": new_parent.id},
            context=self.get_context(),
            partial=True
        )
        self.assertTrue(serializer.is_valid())
        folder = serializer.save()

        self.assertEqual(folder.parent, new_parent)
        mock_task.assert_called_once_with(folder.id)

    @patch("apps.cloud_storage.serializers.folder_serializer.update_folder_file_paths_task.delay")
    def test_update_name_and_parent_triggers_path_update_once(self, mock_task):
        new_parent = FolderFactory(name="NP", user=self.user)
        data = {"name": "Combo", "parent_id": new_parent.id}
        serializer = self.serializer(
            instance=self.parent_folder,
            data=data,
            context=self.get_context(),
            partial=True
        )
        self.assertTrue(serializer.is_valid())
        folder = serializer.save()

        self.assertEqual(folder.name, "Combo")
        self.assertEqual(folder.parent, new_parent)
        mock_task.assert_called_once_with(folder.id)

    @patch("apps.cloud_storage.serializers.folder_serializer.update_folder_file_paths_task.delay")
    def test_partial_update_without_name_or_parent_does_not_trigger_task(self, mock_task):
        serializer = self.serializer(instance=self.parent_folder, data={}, context=self.get_context(), partial=True)
        self.assertTrue(serializer.is_valid())
        serializer.save()

        mock_task.assert_not_called()

    def test_get_subfolders_count(self):
        FolderFactory(name="child 1", user=self.user, parent=self.parent_folder)
        FolderFactory(name="child 2", user=self.user, parent=self.parent_folder)

        serializer = self.serializer(Folder.objects.filter(parent__isnull=True, user=self.user), many=True,
                                     context=self.get_context())

        self.assertEqual(serializer.data[0].get("subfolders_count"), 2)
        self.assertEqual(serializer.data[0].get("files_count"), 0)

    def test_get_files_count(self):
        CloudFileFactory(folder=self.parent_folder)
        CloudFileFactory(folder=self.parent_folder)

        serializer = self.serializer(Folder.objects.filter(parent__isnull=True, user=self.user), many=True,
                                     context=self.get_context())

        self.assertEqual(serializer.data[0].get("subfolders_count"), 0)
        self.assertEqual(serializer.data[0].get("files_count"), 2)
