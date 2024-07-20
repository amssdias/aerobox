from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from apps.users.views import UserCreateView

app_name = "users"

urlpatterns = [
    path("", UserCreateView.as_view(), name="user"),
    path("login/", obtain_auth_token, name="user-login"),
]
