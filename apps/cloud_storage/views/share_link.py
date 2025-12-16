from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status, authentication
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response

from apps.cloud_storage.exceptions import (
    FolderSharingNotAllowed,
    ShareLinkLimitReached,
    ShareLinkExpirationTooLong,
    ShareLinkPasswordNotAllowed,
)
from apps.cloud_storage.models import ShareLink
from apps.cloud_storage.pagination import ShareLinkPagination
from apps.cloud_storage.serializers.share_link_serializer import ShareLinkSerializer


@extend_schema(tags=["API - Share Links / Private"])
class ShareLinkViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing file sharing links (ShareLink).
    Users can create, list, revoke and delete their own share links.
    Behavior is controlled by the 'file_sharing' feature configuration.
    """

    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ShareLinkSerializer
    pagination_class = ShareLinkPagination

    def get_queryset(self):
        filters = {"owner": self.request.user}

        if self.action in ("update", "partial_update"):
            now = timezone.now()
            filters["revoked_at__isnull"] = True
            filters["expires_at__gt"] = now

        return (
            ShareLink.objects.prefetch_related("files", "folders")
            .filter(**filters)
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        user = self.request.user
        self.check_share_link_permissions(user, serializer, create=True)
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        self.check_share_link_permissions(user, serializer, create=False)
        super().perform_update(serializer)

    @staticmethod
    def check_share_link_permissions(user, serializer, create):
        try:
            user.validate_create_or_update_sharelink(serializer.validated_data, create)
        except FolderSharingNotAllowed:
            raise PermissionDenied(
                _(
                    "Your plan does not allow folder sharing. Upgrade to Pro to enable it."
                )
            )
        except ShareLinkLimitReached:
            raise ValidationError(
                {
                    "non_field_errors": [
                        _(
                            "You have reached the maximum number of active share links for your plan."
                        )
                    ]
                }
            )
        except ShareLinkExpirationTooLong:
            raise ValidationError(
                {
                    "non_field_errors": [
                        _("Expiration exceeds the maximum allowed for your plan.")
                    ]
                }
            )
        except ShareLinkPasswordNotAllowed:
            raise PermissionDenied(
                _("Your plan does not allow password-protected links.")
            )

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        """
        After revocation the link is considered inactive but kept for history.
        """
        link = self.get_object()

        if link.revoked_at is not None:
            return Response(
                {"detail": _("This link is already revoked.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link.revoked_at = timezone.now()
        link.save(update_fields=["revoked_at"])

        serializer = self.get_serializer(link)
        return Response(serializer.data, status=status.HTTP_200_OK)
