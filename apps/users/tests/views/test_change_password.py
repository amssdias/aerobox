from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.factories.user_factory import UserFactory


@override_settings(AUTH_PASSWORD_VALIDATORS=[])
class ChangePasswordViewTest(APITestCase):

    def setUp(self):
        self.user = UserFactory(
            username="dias",
            email="dias@example.com",
            password="OldPassword123!",
        )
        self.url = reverse("users:change-password")
        self.client.force_authenticate(user=self.user)

    def _get_payload(
            self,
            old_password="OldPassword123!",
            new_password="NewPassword456!",
            new_password_again="NewPassword456!",
    ):
        return {
            "old_password": old_password,
            "new_password": new_password,
            "new_password_again": new_password_again,
        }

    def test_authenticated_user_can_change_password(self):
        response = self.client.post(self.url, data=self._get_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"detail": "Password updated successfully."},
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword456!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))

    def test_unauthenticated_user_cannot_change_password(self):
        self.client.logout()
        response = self.client.post(self.url, data=self._get_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

    def test_returns_400_when_old_password_is_wrong(self):
        response = self.client.post(
            self.url,
            data=self._get_payload(old_password="WrongPassword999!"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)
        self.assertEqual(response.data["old_password"][0], "Old password is incorrect.")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

    def test_returns_400_when_new_passwords_do_not_match(self):
        response = self.client.post(
            self.url,
            data=self._get_payload(
                new_password="NewPassword456!",
                new_password_again="AnotherPassword789!",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password_again", response.data)
        self.assertEqual(
            response.data["new_password_again"][0],
            "New passwords do not match.",
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

    def test_returns_400_when_new_password_is_same_as_old_password(self):
        response = self.client.post(
            self.url,
            data=self._get_payload(
                old_password="OldPassword123!",
                new_password="OldPassword123!",
                new_password_again="OldPassword123!",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
        self.assertEqual(
            response.data["new_password"][0],
            "New password must be different from the old password.",
        )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

    def test_returns_400_when_old_password_is_missing(self):
        payload = self._get_payload()
        payload.pop("old_password")

        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)
        self.assertEqual(response.data["old_password"][0], "This field is required.")

    def test_returns_400_when_new_password_is_missing(self):
        payload = self._get_payload()
        payload.pop("new_password")

        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
        self.assertEqual(response.data["new_password"][0], "This field is required.")

    def test_returns_400_when_new_password_again_is_missing(self):
        payload = self._get_payload()
        payload.pop("new_password_again")

        response = self.client.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password_again", response.data)
        self.assertEqual(
            response.data["new_password_again"][0],
            "This field is required.",
        )

    def test_password_is_not_changed_when_request_is_invalid(self):
        response = self.client.post(
            self.url,
            data=self._get_payload(
                new_password="NewPassword456!",
                new_password_again="DifferentPassword999!",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))
        self.assertFalse(self.user.check_password("NewPassword456!"))

    def test_user_can_authenticate_with_new_password_after_change(self):
        response = self.client.post(self.url, data=self._get_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=None)

        login_success = self.client.login(
            username="dias",
            password="NewPassword456!",
        )
        self.assertTrue(login_success)

    def test_old_password_no_longer_works_after_change(self):
        response = self.client.post(self.url, data=self._get_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=None)

        login_success = self.client.login(
            username="dias",
            password="OldPassword123!",
        )
        self.assertFalse(login_success)

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                "OPTIONS": {"min_length": 12},
            }
        ]
    )
    def test_returns_400_when_new_password_fails_django_password_validation(self):
        response = self.client.post(
            self.url,
            data=self._get_payload(
                new_password="short1!",
                new_password_again="short1!",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))
