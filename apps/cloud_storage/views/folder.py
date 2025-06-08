from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cloud_storage.models import Folder
from apps.cloud_storage.serializers import FolderSerializer, FolderDetailSerializer


@extend_schema_view(
    partial_update=extend_schema(exclude=True),
)
@extend_schema(tags=["API - Cloud Storage"])
class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = Folder.objects.filter(user=self.request.user)
        if self.action == "list":
            queryset = queryset.filter(parent__isnull=True)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Returns a list of top-level folders belonging to the user.

        Only folders without a parent (i.e., main/root folders) are included in the response.
        """
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self, *args, **kwargs):
        if self.action == "retrieve":
            return FolderDetailSerializer
        return FolderSerializer

    def destroy(self, request, *args, **kwargs):
        """
        Deletes a folder if it is empty and not protected.

        A folder is considered empty if it has no subfolders and no files.
        Deletion is blocked if the folder:
        - Is marked as protected (`is_protected=True`) -> Not implemented yet
        - Contains any direct subfolders or files
        """
        folder = self.get_object()

        if folder.subfolders.exists() or folder.files.filter(deleted_at__isnull=True).exists():
            return Response({"detail": _("Cannot delete a folder that contains files or subfolders.")}, status=400)

        folder.delete()
        return Response(status=204)
