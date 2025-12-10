import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.serializers.public_share_serializer import (
    PublicShareLinkMetaSerializer,
    PublicShareLinkDetailSerializer,
)
from apps.cloud_storage.services.storage.s3_service import S3Service
from apps.cloud_storage.views.mixins.share_link import ShareLinkMixin

logger = logging.getLogger("aerobox")


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


class PublicShareLinkFileDownloadView(ShareLinkMixin, APIView):
    """
    Public endpoint to get a presigned download URL for a file
    belonging to a ShareLink.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, token, file_id):
        share_link = self.get_object()
        self.validate_share_link(share_link)

        # Password check
        if share_link.password:
            password = request.data.get("password")
            if not password or not share_link.check_password(password):
                raise ValidationError({"password": _("Invalid password.")})

        file_obj = get_object_or_404(
            CloudFile.objects.select_related("folder"), id=file_id
        )
        if not share_link.can_access_file(file_obj):
            raise NotFound(_("File not found for this share link."))

        s3_service = S3Service()
        try:
            download_url = s3_service.generate_presigned_download_url(
                object_name=file_obj.s3_key
            )
        except Exception as e:
            logger.error(
                "Failed to generate S3 presigned URL for file_id=%s token=%s error=%s",
                file_id,
                token,
                str(e),
                exc_info=True,
            )
            raise ValidationError(
                {"error": _("Could not generate download URL. Please try again later.")}
            )

        return Response({"url": download_url}, status=status.HTTP_200_OK)
