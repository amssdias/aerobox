from django.test import RequestFactory, TestCase, override_settings
from rest_framework.serializers import ErrorDetail

from apps.users.api.serializers import ChangePasswordSerializer
from apps.users.factories.user_factory import UserFactory


@override_settings(AUTH_PASSWORD_VALIDATORS=[])
class ChangePasswordSerializerTest(TestCase):

    def setUp(self):
        self.user = UserFactory(
            username="dias",
            email="dias@example.com",
            password="OldPassword123!",
        )
        self.factory = RequestFactory()

    def _get_request(self, user=None):
        request = self.factory.post("/fake-url/")
        request.user = user or self.user
        return request

    def _get_serializer(self, data, user=None):
        request = self._get_request(user=user)
        return ChangePasswordSerializer(
            data=data,
            context={"request": request},
        )

    def test_serializer_is_valid_with_correct_data(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_old_password_is_required(self):
        serializer = self._get_serializer(
            data={
                "new_password": "NewPassword456!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("old_password", serializer.errors)
        self.assertEqual(
            serializer.errors["old_password"][0],
            ErrorDetail(string="This field is required.", code="required"),
        )

    def test_new_password_is_required(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)
        self.assertEqual(
            serializer.errors["new_password"][0],
            ErrorDetail(string="This field is required.", code="required"),
        )

    def test_new_password_again_is_required(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password_again", serializer.errors)
        self.assertEqual(
            serializer.errors["new_password_again"][0],
            ErrorDetail(string="This field is required.", code="required"),
        )

    def test_validation_fails_when_old_password_is_incorrect(self):
        serializer = self._get_serializer(
            data={
                "old_password": "WrongPassword999!",
                "new_password": "NewPassword456!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("old_password", serializer.errors)
        self.assertEqual(
            serializer.errors["old_password"][0],
            "Old password is incorrect.",
        )

    def test_validation_fails_when_new_passwords_do_not_match(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!",
                "new_password_again": "AnotherPassword789!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password_again", serializer.errors)
        self.assertEqual(
            serializer.errors["new_password_again"][0],
            "New passwords do not match.",
        )

    def test_validation_fails_when_new_password_is_same_as_old_password(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "OldPassword123!",
                "new_password_again": "OldPassword123!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)
        self.assertEqual(
            serializer.errors["new_password"][0],
            "New password must be different from the old password.",
        )

    def test_save_updates_user_password(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword456!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))

    def test_save_returns_user_instance(self):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "NewPassword456!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        returned_user = serializer.save()

        self.assertEqual(returned_user.pk, self.user.pk)

    def test_password_is_not_changed_when_serializer_is_invalid(self):
        serializer = self._get_serializer(
            data={
                "old_password": "WrongPassword999!",
                "new_password": "NewPassword456!",
                "new_password_again": "NewPassword456!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))
        self.assertFalse(self.user.check_password("NewPassword456!"))

    def test_password_fields_preserve_whitespace_because_trim_is_disabled(self):
        user = UserFactory(
            username="whitespace_user",
            email="white@example.com",
            password="  OldPassword123!  ",
        )

        serializer = self._get_serializer(
            user=user,
            data={
                "old_password": "  OldPassword123!  ",
                "new_password": "  NewPassword456!  ",
                "new_password_again": "  NewPassword456!  ",
            },
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        user.refresh_from_db()
        self.assertTrue(user.check_password("  NewPassword456!  "))
        self.assertFalse(user.check_password("NewPassword456!"))

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
                "OPTIONS": {"min_length": 12},
            }
        ]
    )
    def test_validation_fails_when_new_password_does_not_pass_django_password_validators(
            self,
    ):
        serializer = self._get_serializer(
            data={
                "old_password": "OldPassword123!",
                "new_password": "short1!",
                "new_password_again": "short1!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
