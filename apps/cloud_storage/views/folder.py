from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, filters, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cloud_storage.domain.exceptions.folder import FolderContainsFilesOrSubfoldersError
from apps.cloud_storage.filters.folder_filter import FolderFilter
from apps.cloud_storage.models import Folder
from apps.cloud_storage.serializers import FolderSerializer, FolderDetailSerializer
from apps.cloud_storage.services.folders.delete_folder import delete_folder


@extend_schema_view(
    partial_update=extend_schema(exclude=True),
)
@extend_schema(tags=["API - Cloud Storage"])
class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filter_backends = [filters.OrderingFilter, rest_framework.DjangoFilterBackend]
    filterset_class = FolderFilter
    ordering_fields = ["name"]
    ordering = ["name"]

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

        try:
            delete_folder(folder_id=folder.id)
        except FolderContainsFilesOrSubfoldersError:
            return Response(
                {"detail": _("Cannot delete a folder that contains files or subfolders.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=204)
