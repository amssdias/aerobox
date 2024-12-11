from django.test import SimpleTestCase
from django.urls import reverse, resolve
from rest_framework.authtoken.views import obtain_auth_token

from apps.users.views import (
    UserCreateView,
    CustomPasswordResetView,
    CustomPasswordResetConfirmView,
)


class TestUsersAppUrls(SimpleTestCase):

    def test_user_create_url_is_resolved(self):
        url = reverse("users:user")
        self.assertEqual(resolve(url).func.view_class, UserCreateView)

    def test_user_login_url_is_resolved(self):
        url = reverse("users:user-login")
        self.assertEqual(resolve(url).func, obtain_auth_token)

    def test_password_reset_url_is_resolved(self):
        url = reverse("users:password_reset")
        self.assertEqual(resolve(url).func.view_class, CustomPasswordResetView)

    def test_password_reset_confirm_url_is_resolved(self):
        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": "test-uid", "token": "test-token"},
        )
        self.assertEqual(resolve(url).func.view_class, CustomPasswordResetConfirmView)
