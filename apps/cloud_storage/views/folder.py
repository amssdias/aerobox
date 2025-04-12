from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.cloud_storage.models import Folder
from apps.cloud_storage.serializers import FolderSerializer, FolderDetailSerializer


@extend_schema_view(
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True)
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
