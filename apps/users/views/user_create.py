from rest_framework.generics import CreateAPIView
from apps.users.serializers import UserSerializer
from config.api_docs.custom_extensions import api_users_tag


@api_users_tag()
class UserCreateView(CreateAPIView):
    serializer_class = UserSerializer
