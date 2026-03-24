from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from apps.users.api.views import (
    UserCreateView,
    CustomPasswordResetView,
    CustomPasswordResetConfirmView,
    ChangePasswordView,
)

app_name = "users"

urlpatterns = [
    path("", UserCreateView.as_view(), name="user"),
    path("login/", obtain_auth_token, name="user-login"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset-confirm/",
        CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
