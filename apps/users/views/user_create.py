from django.contrib.auth import get_user_model
from rest_framework import mixins, generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.users.serializers import UserSerializer, UserUpdateSerializer
from config.api_docs.custom_extensions import api_users_tag

User = get_user_model()

@api_users_tag()
class UserCreateView(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView
):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserSerializer
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
