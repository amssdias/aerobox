from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from apps.users.views import UserCreateView
from apps.users.views.password_reset import CustomPasswordResetView, CustomPasswordResetConfirmView

app_name = "users"

urlpatterns = [
    path("", UserCreateView.as_view(), name="user"),
    path("login/", obtain_auth_token, name="user-login"),

    path("password-reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path("password-reset-confirm/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]