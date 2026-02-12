import logging

from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, filters
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cloud_storage.api.error_messages import get_error_message
from apps.cloud_storage.api.filters.cloud_file_filter import CloudFileFilter
from apps.cloud_storage.api.pagination import CloudFilesPagination
from apps.cloud_storage.api.serializers import CloudFilesSerializer
from apps.cloud_storage.api.serializers.cloud_files import (
    CloudFileMetaPatchSerializer,
    CloudFileUpdateSerializer,
)
from apps.cloud_storage.constants.cloud_files import SUCCESS, FAILED
from apps.cloud_storage.domain.exceptions.file import FileNotDeletedError
from apps.cloud_storage.integrations.storage.s3_service import S3Service
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.services.files.create_presigned_upload import (
    prepare_file_upload,
)
from apps.cloud_storage.services.files.delete_file import (
    permanent_delete_file,
)
from apps.cloud_storage.services.files.file_upload_finalizer_service import (
    FileUploadFinalizerService,
)
from apps.cloud_storage.tasks.delete_files import clear_all_deleted_files_from_user
from config.api_docs.openapi_schemas import RESPONSE_SCHEMA_GET_PRESIGNED_URL

logger = logging.getLogger("aerobox")


@extend_schema(tags=["API - Cloud Storage"])
class CloudStorageViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CloudFilesSerializer
    queryset = CloudFile.not_deleted.all()
    filter_backends = [filters.OrderingFilter, rest_framework.DjangoFilterBackend]
    filterset_class = CloudFileFilter
    ordering_fields = ["file_name", "size", "content_type", "created_at"]
    ordering = ["id"]
    pagination_class = CloudFilesPagination

    def get_queryset(self):
        user = self.request.user

        if self.action in [
            "deleted_files",
            "restore_deleted_file",
            "permanent_delete_file",
            "permanent_delete_all_files",
        ]:
            return CloudFile.deleted.filter(user=user).order_by("deleted_at")

        if self.action == "update":
            return CloudFile.not_deleted.user_success_files(user)

        return CloudFile.not_deleted.filter(user=user).order_by("id")

    def get_serializer_class(self):
        if self.action == "partial_update":
            return CloudFileMetaPatchSerializer
        elif self.action == "update":
            return CloudFileUpdateSerializer
        return CloudFilesSerializer

    @extend_schema(
        responses={200: RESPONSE_SCHEMA_GET_PRESIGNED_URL},
    )
    def create(self, request, *args, **kwargs):
        """
        Save file info on DB and get a presigned URL to upload on cloud.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        storage = S3Service()
        result = prepare_file_upload(
            storage=storage,
            user=request.user,
            file_name=serializer.validated_data["file_name"],
            content_type=serializer.validated_data["content_type"],
        )

        # Save file metadata in DB
        serializer.validated_data["s3_key"] = result.file_path
        self.perform_create(serializer)

        return Response(
            {"presigned-url": result.presigned_url, "file": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def list(self, request):
        return super(CloudStorageViewSet, self).list(request)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a file info by ID
        """
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Rename a file or change it's folder.
        """
        cloud_file = self.get_object()

        serializer = self.get_serializer(instance=cloud_file, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(
            {"message": _("File successfully updated.")}, status=status.HTTP_200_OK
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        new_status = serializer.validated_data.get("status")

        if new_status == FAILED:
            msg = get_error_message(instance.error_code)
            return Response(
                {
                    "detail": msg,
                    "code": instance.error_code,
                },
                status=status.HTTP_200_OK,
            )

        if new_status == SUCCESS:
            finalizer = FileUploadFinalizerService()
            ok = finalizer.finalize(instance)

            if not ok:
                msg = get_error_message(instance.error_code)
                return Response(
                    {
                        "detail": msg,
                        "code": instance.error_code,
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Soft delete the file by setting 'deleted_at' instead of deleting it."""
        instance = self.get_object()
        instance.soft_delete()
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        context = super().get_serializer_context()

        # Differentiate list vs. detail views
        context["is_detail"] = self.action == "retrieve"
        return context

    @action(detail=False, methods=["get"], url_path="deleted")
    def deleted_files(self, request):
        """Get deleted files from a user"""

        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(request=None)
    @action(detail=True, methods=["patch"], url_path="restore")
    def restore_deleted_file(self, request, pk=None):
        """
        Restore a deleted file (sets is_deleted=False)
        """
        file = self.get_object()

        try:
            file.restore()
        except FileNotDeletedError:
            return Response(
                {"detail": _("File is not deleted.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"id": file.id, "restored": True}, status=status.HTTP_200_OK)

    @extend_schema(request=None)
    @action(detail=True, methods=["delete"], url_path="permanent-delete")
    def permanent_delete_file(self, request, pk=None):
        """
        Permanent delete a file in BD and AWS S3
        """
        file = self.get_object()

        s3_service = S3Service()
        permanent_delete_file(s3_service, file)

        return Response(
            {"message": _("File permanently deleted.")},
            status=status.HTTP_204_NO_CONTENT,
        )

    @extend_schema(request=None)
    @action(detail=False, methods=["delete"], url_path="permanent-delete-files")
    def permanent_delete_all_files(self, request, pk=None):
        """
        Permanent delete all files in BD and AWS S3
        """

        all_deleted_files = self.get_queryset()
        if not all_deleted_files:
            return Response(
                {"message": _("No files found in the recycle bin to delete.")},
                status=status.HTTP_200_OK,
            )

        all_deleted_files_count = all_deleted_files.count()
        clear_all_deleted_files_from_user.delay(self.request.user.id)

        return Response(
            {
                "message": _(
                    "All files in the recycle bin have been permanently deleted."
                ),
                "deleted_count": all_deleted_files_count,
            },
            status=status.HTTP_204_NO_CONTENT,
        )
