import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError, NotFound, AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.serializers import FolderDetailSerializer
from apps.cloud_storage.serializers.public_share_serializer import (
    PublicShareLinkDetailSerializer, ShareLinkPasswordSerializer,
)
from apps.cloud_storage.services.storage.s3_service import S3Service
from apps.cloud_storage.views.mixins.share_link import ShareLinkMixin, ShareLinkAccessMixin

logger = logging.getLogger("aerobox")


@extend_schema(tags=["API - File Sharing"])
class PublicShareLinkDetail(ShareLinkMixin, ShareLinkAccessMixin, APIView):
    """
    Public endpoint to access a share link by token.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        share_link = self.get_object()
        self.validate_share_link(share_link)
        self.require_valid_access(request, share_link)

        serializer = PublicShareLinkDetailSerializer(
            share_link, context={"user": share_link.owner}
        )

        return Response(serializer.data)


@extend_schema(tags=["API - File Sharing"])
class PublicShareLinkAuthView(ShareLinkMixin, ShareLinkAccessMixin, APIView):
    """
    Validates the password for a ShareLink and returns an access token
    that the frontend must send in the `X-ShareLink-Access` header on
    subsequent requests (folder browse, file download, etc.).
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, token, *args, **kwargs):
        share_link = self.get_object()

        serializer = ShareLinkPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_password = serializer.validated_data.get("password") or ""

        if share_link.password:
            if not share_link.check_password(raw_password):
                raise AuthenticationFailed(_("Invalid password for this share link."))
        else:
            # If the link does NOT have a password, we don't need to validate anything.
            # You can still choose to return access_token = null here.
            access_token = None

            return Response(
                {
                    "access_token": access_token,
                    "requires_password": False,
                    "expires_in": None,
                },
                status=status.HTTP_200_OK,
            )

        access_token = self.build_access_token(share_link)

        return Response(
            {
                "access_token": access_token,
                "expires_in": self.access_max_age,  # e.g. 3600 seconds
                "token_type": "sharelink_access",
            },
            status=status.HTTP_200_OK,
        )


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
