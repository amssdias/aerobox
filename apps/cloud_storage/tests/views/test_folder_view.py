from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.models import Folder
from apps.cloud_storage.tests.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.tests.factories.folder_factory import FolderFactory
from apps.subscriptions.factories.plan_factory import PlanFactory
from apps.subscriptions.factories.subscription import SubscriptionFactory
from apps.subscriptions.models import Plan
from apps.users.factories.user_factory import UserFactory


class FolderViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username="test-user-1")
        cls.other_user = UserFactory(username="test-user-2")

        cls.root_folder = FolderFactory(name="Root", user=cls.user)
        cls.subfolder = FolderFactory(name="Sub", parent=cls.root_folder, user=cls.user)
        cls.other_user_folder = FolderFactory(name="OtherUserFolder", user=cls.other_user)

        cls.plan = Plan.objects.get(is_free=True)
        cls.subscription = SubscriptionFactory(
            user=cls.user,
            plan=cls.plan,
            end_date=timezone.now().date() + timedelta(days=30)
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_list_folders_returns_only_root_folders(self):
        response = self.client.get(reverse("folders-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.root_folder.id)
        self.assertIsNone(response.data[0]["parent"])

    def test_retrieve_folder_returns_correct_data(self):
        response = self.client.get(reverse("folders-detail", args=[self.root_folder.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.root_folder.id)
        self.assertEqual(response.data["name"], self.root_folder.name)
        self.assertEqual(response.data["subfolders"][0]["id"], self.subfolder.id)
        self.assertEqual(response.data["subfolders"][0]["name"], self.subfolder.name)

    def test_retrieve_folder_from_another_user_returns_404(self):
        response = self.client.get(reverse("folders-detail", args=[self.other_user_folder.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_empty_folder(self):
        empty_folder = FolderFactory(name="Deletable", user=self.user)
        response = self.client.delete(reverse("folders-detail", args=[empty_folder.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Folder.objects.filter(id=empty_folder.id).exists())

    def test_delete_folder_with_subfolder_fails(self):
        response = self.client.delete(reverse("folders-detail", args=[self.root_folder.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertTrue("contains files or subfolders" in response.data["detail"])

    def test_delete_folder_with_file_fails(self):
        folder_with_file = FolderFactory(name="HasFile", user=self.user)
        CloudFileFactory(folder=folder_with_file, file_name="test.pdf")

        response = self.client.delete(reverse("folders-detail", args=[folder_with_file.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_delete_folder_containing_soft_deleted_file(self):
        folder_with_file = FolderFactory(name="HasFile", user=self.user)
        CloudFileFactory(
            folder=folder_with_file,
            file_name="test.pdf",
            deleted_at=timezone.now(),
        )
        response = self.client.delete(reverse("folders-detail", args=[folder_with_file.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Folder.objects.filter(id=folder_with_file.id).exists())

    def test_delete_folder_from_another_user_returns_404(self):
        response = self.client.delete(reverse("folders-detail", args=[self.other_user_folder.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_folder_root(self):
        data = {
            "name": "My Folder",
            "parent_id": ""
        }
        total_folders = Folder.objects.count()
        response = self.client.post(reverse("folders-list"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Folder.objects.count(), total_folders + 1)
        self.assertEqual(response.data["name"], "My Folder")
        self.assertIsNone(response.data["parent"])
        self.assertEqual(response.data["user"], self.user.id)
        self.assertTrue(Folder.objects.filter(id=response.data["id"]).exists())

    def test_create_folder_unauthenticated(self):
        self.client.force_authenticate(user=None)
        data = {"name": "Private Folder"}
        response = self.client.post(reverse("folders-list"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_folder_without_subscription(self):
        data = {
            "name": "My Folder",
            "parent_id": ""
        }

        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(reverse("folders-list"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You need an active subscription to use this feature. Please check your billing or subscribe to a plan.",
            response.data["non_field_errors"][0])

    def test_create_folder_without_feature_in_subscription(self):
        user = UserFactory(username="test-user-3")

        plan = PlanFactory(name={"en": "Basic Plan DEMO without folder creation"})
        SubscriptionFactory(
            user=user,
            plan=plan,
            end_date=timezone.now().date() + timedelta(days=30)
        )

        data = {
            "name": "My Folder",
            "parent_id": ""
        }
        self.client.force_authenticate(user=user)
        response = self.client.post(reverse("folders-list"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Your current subscription plan does not include the folder creation feature. Please upgrade your plan to access this functionality.",
            response.data["non_field_errors"][0])

    def test_update_folder(self):
        folder = FolderFactory(name="Old Name", user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        data = {
            "name": "Updated Name",
            "parent_id": ""
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        folder.refresh_from_db()
        self.assertEqual(folder.name, "Updated Name")

    def test_update_folder_unauthenticated(self):
        folder = FolderFactory(name="Name", user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})

        self.client.force_authenticate(user=None)
        response = self.client.patch(url, {"name": "Hacked"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_folder_from_other_user(self):
        folder = FolderFactory(name="Folder from user 1", user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        data = {
            "name": "Updated Name",
            "parent_id": ""
        }

        self.client.force_authenticate(user=self.other_user)
        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_folder_without_subscription(self):
        data = {
            "name": "My Folder",
            "parent_id": ""
        }

        self.client.force_authenticate(user=self.other_user)
        response = self.client.put(
            reverse("folders-detail", kwargs={"pk": self.other_user_folder.pk}),
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You need an active subscription to use this feature. Please check your billing or subscribe to a plan.",
            response.data["non_field_errors"][0])

    def test_update_folder_without_feature_in_subscription(self):
        user = UserFactory(username="test-user-4")
        folder = FolderFactory(name="Folder user 4", user=user)
        plan = PlanFactory(name={"en": "Basic Plan DEMO without folder creation"})
        SubscriptionFactory(
            user=user,
            plan=plan,
            end_date=timezone.now().date() + timedelta(days=30)
        )

        data = {
            "name": "My Folder",
            "parent_id": ""
        }

        self.client.force_authenticate(user=user)
        response = self.client.put(
            reverse("folders-detail", kwargs={"pk": folder.pk}),
            data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Your current subscription plan does not include the folder creation feature. Please upgrade your plan to access this functionality.",
            response.data["non_field_errors"][0])

    def test_update_folder_name_only(self):
        folder = FolderFactory(name="Original", user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        response = self.client.put(url, {"name": "Renamed", "parent_id": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        folder.refresh_from_db()
        self.assertEqual(folder.name, "Renamed")

    def test_update_folder_parent_only(self):
        parent = FolderFactory(user=self.user)
        folder = FolderFactory(name="Child", user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        response = self.client.put(url, {"name": folder.name, "parent_id": parent.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        folder.refresh_from_db()
        self.assertEqual(folder.parent_id, parent.id)

    def test_update_folder_name_and_parent(self):
        old_parent = FolderFactory(user=self.user)
        new_parent = FolderFactory(user=self.user)
        folder = FolderFactory(name="ToMove", user=self.user, parent=old_parent)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        response = self.client.put(url, {"name": "MovedAndRenamed", "parent_id": new_parent.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        folder.refresh_from_db()
        self.assertEqual(folder.name, "MovedAndRenamed")
        self.assertEqual(folder.parent_id, new_parent.id)

    def test_update_folder_invalid_name_backslash(self):
        folder = FolderFactory(user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        response = self.client.put(url, {"name": "Invalid\\Name", "parent_id": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_update_folder_invalid_name_trailing_slash(self):
        folder = FolderFactory(user=self.user)
        url = reverse("folders-detail", kwargs={"pk": folder.pk})
        response = self.client.put(url, {"name": "EndsWith/", "parent_id": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_update_folder_to_existing_name_in_same_parent(self):
        parent = FolderFactory(user=self.user)
        FolderFactory(name="Existing", user=self.user, parent=parent)
        target = FolderFactory(name="Renamable", user=self.user, parent=parent)
        url = reverse("folders-detail", kwargs={"pk": target.pk})
        response = self.client.put(url, {"name": "Existing", "parent_id": parent.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
