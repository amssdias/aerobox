from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from apps.users.api.serializers.user_serializer import UserDetailsSerializer
from config.api_docs.custom_extensions import api_users_tag


@api_users_tag()
class UserDetailsView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailsSerializer

    def get_object(self):
        return self.request.user
