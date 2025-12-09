from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cloud_storage.serializers.public_share_serializer import (
    PublicShareLinkMetaSerializer,
    PublicShareLinkDetailSerializer,
)
from apps.cloud_storage.views.mixins.share_link import ShareLinkMixin


@extend_schema(tags=["API - File Sharing"])
class PublicShareLinkDetail(ShareLinkMixin, APIView):
    """
    Public endpoint to access a share link by token.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        share_link = self.get_object()
        self.validate_share_link(share_link)

        if share_link.password:
            # Password-protected → only send meta
            serializer = PublicShareLinkMetaSerializer(share_link)
        else:
            # Public link → send full details
            serializer = PublicShareLinkDetailSerializer(
                share_link, context={"user": share_link.owner}
            )

        return Response(serializer.data)


@extend_schema(tags=["API - File Sharing"])
class PublicShareLinkUnlock(ShareLinkMixin, APIView):
    """
    Public endpoint to access a share link by token WITH PASSWORD to unlock.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        password = request.data.get("password", "")

        share_link = self.get_object()
        self.validate_share_link(share_link)

        if not share_link.password:
            return Response(
                {"detail": _("This link is not password protected.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not share_link.check_password(password):
            return Response(
                {"detail": _("Invalid password.")}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PublicShareLinkDetailSerializer(
            share_link, context={"user": share_link.owner}
        )
        return Response(serializer.data)
