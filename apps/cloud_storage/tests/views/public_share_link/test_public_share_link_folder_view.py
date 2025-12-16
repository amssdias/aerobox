from django.core.signing import TimestampSigner
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cloud_storage.factories.cloud_file_factory import CloudFileFactory
from apps.cloud_storage.factories.folder_factory import FolderFactory
from apps.cloud_storage.factories.share_link_factory import ShareLinkFactory
from apps.users.factories.user_factory import UserFactory


class TestPublicShareLinkFolderView(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = UserFactory()
        cls.other_user = UserFactory()

        # Folder tree for owner
        cls.root = FolderFactory(name="root", parent=None, user=cls.owner)
        cls.parent = FolderFactory(name="parent", parent=cls.root, user=cls.owner)
        cls.child = FolderFactory(name="child", parent=cls.parent, user=cls.owner)

        # Another root tree not shared
        cls.other_root = FolderFactory(name="other_root", parent=None, user=cls.owner)
        cls.other_child = FolderFactory(
            name="other_child", parent=cls.other_root, user=cls.owner
        )

        # Folder that belongs to a different user
        cls.foreign_root = FolderFactory(
            name="foreign_root", parent=None, user=cls.other_user
        )
        cls.foreign_child = FolderFactory(
            name="foreign_child", parent=cls.foreign_root, user=cls.other_user
        )

        # Files inside folders (not required for view auth, but validates "contents" path)
        cls.file_in_child = CloudFileFactory(
            file_name="f1", folder=cls.child, user=cls.owner
        )
        cls.file_in_other_child = CloudFileFactory(
            file_name="f2", folder=cls.other_child, user=cls.owner
        )

        # Share links
        cls.share_link_open = ShareLinkFactory(
            owner=cls.owner,
            folders=[cls.root],
        )

        cls.share_link_pw = ShareLinkFactory(
            owner=cls.owner,
            folders=[cls.root],
        )
        cls.password = "secret-password"
        cls.share_link_pw.set_password(cls.password)
        cls.share_link_pw.save()

        cls.share_link_revoked = ShareLinkFactory(
            owner=cls.owner,
            revoked_at=timezone.now(),
            folders=[cls.root],
        )

        cls.share_link_expired = ShareLinkFactory(
            owner=cls.owner, expires_at=timezone.now(), folders=[cls.root]
        )

        cls.signer = TimestampSigner(salt="sharelink-access")
        cls.access_header = "HTTP_X_SHARELINK_ACCESS"
        cls.url_name = "public-sharelink-folder-detail"

    def _url(self, token, folder_id):
        return reverse(self.url_name, kwargs={"token": token, "folder_id": folder_id})

    def _access_token_for(self, share_link):
        return self.signer.sign(str(share_link.pk))

    def test_open_share_link_returns_200(self):
        res = self.client.get(self._url(self.share_link_open.token, self.child.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.child.id)
        self.assertEqual(res.data["name"], self.child.name)

    def test_open_share_link_returns_subfolders_and_files_keys(self):
        res = self.client.get(self._url(self.share_link_open.token, self.child.id))

        self.assertEqual(res.status_code, 200)
        self.assertIn("parent", res.data)
        self.assertIn("subfolders", res.data)
        self.assertIn("files", res.data)

    def test_password_share_link_with_valid_access_header_returns_200(self):
        token = self._access_token_for(self.share_link_pw)
        res = self.client.get(
            self._url(self.share_link_pw.token, self.child.id),
            **{self.access_header: token},
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], self.child.id)

    def test_invalid_token_returns_404_with_custom_message(self):
        res = self.client.get(self._url("does-not-exist", self.child.id))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            res.data["detail"], "The link you’re trying to open doesn’t exist."
        )

    def test_revoked_share_link_returns_410(self):
        res = self.client.get(self._url(self.share_link_revoked.token, self.child.id))

        self.assertEqual(res.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            res.data["detail"], "This link has been disabled by the owner."
        )

    def test_expired_share_link_returns_410(self):
        res = self.client.get(self._url(self.share_link_expired.token, self.child.id))

        self.assertEqual(res.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            res.data["detail"], "This link has expired and can’t be accessed anymore."
        )

    def test_password_required_missing_header_returns_401(self):
        res = self.client.get(self._url(self.share_link_pw.token, self.child.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.data["detail"], "Password required for this share link.")

    def test_password_required_invalid_signature_returns_401(self):
        res = self.client.get(
            self._url(self.share_link_pw.token, self.child.id),
            **{self.access_header: "totally-invalid"},
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.data["detail"], "Invalid access token.")

    def test_password_required_token_for_other_sharelink_pk_returns_401(self):
        # build token for open link but use it on password link
        wrong = self._access_token_for(self.share_link_open)
        res = self.client.get(
            self._url(self.share_link_pw.token, self.child.id),
            **{self.access_header: wrong},
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.data["detail"], "Invalid access token.")

    def test_folder_not_found_for_owner_returns_404(self):
        res = self.client.get(self._url(self.share_link_open.token, 999999999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_folder_belongs_to_other_user_returns_404(self):
        res = self.client.get(
            self._url(self.share_link_open.token, self.foreign_child.id)
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_404_when_folder_root_is_not_in_share_link_folders(self):
        res = self.client.get(
            self._url(self.share_link_open.token, self.other_child.id)
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            res.data["detail"], "The folder you’re trying to open doesn’t exist."
        )

    def test_allows_access_to_root_itself_when_root_is_shared(self):
        res = self.client.get(self._url(self.share_link_open.token, self.root.id))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], self.root.id)

    def test_allows_access_to_deep_descendant_when_root_is_shared(self):
        res = self.client.get(self._url(self.share_link_open.token, self.child.id))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], self.child.id)

    def test_open_share_link_ignores_access_header_and_still_works(self):
        res = self.client.get(
            self._url(self.share_link_open.token, self.child.id),
            **{self.access_header: "garbage"},
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], self.child.id)
