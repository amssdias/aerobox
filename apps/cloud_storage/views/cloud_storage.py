import logging

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cloud_storage.exceptions import FileUploadError
from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.cloud_storage.serializers.cloud_files import CloudFileMetaPatchSerializer, CloudFileUpdateSerializer
from apps.cloud_storage.services import S3Service
from apps.cloud_storage.utils.hash_utils import generate_unique_hash
from apps.cloud_storage.utils.path_utils import build_s3_path
from config.api_docs.openapi_schemas import RESPONSE_SCHEMA_GET_PRESIGNED_URL

logger = logging.getLogger("aerobox")


@extend_schema(tags=["API - Cloud Storage"])
class CloudStorageViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CloudFilesSerializer
    queryset = CloudFile.not_deleted.all().order_by("id")

    def get_queryset(self):
        user = self.request.user

        if self.action == "deleted_files":
            return CloudFile.deleted.filter(user=user).order_by("id")

        if self.action == "update":
            return CloudFile.not_deleted.user_success_files(user).order_by("id")

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

        # Generate a presigned URL for uploading
        s3_service = S3Service()
        hashed_file_name = generate_unique_hash(serializer.validated_data.get("file_name"))
        file_path = build_s3_path(
            user_id=self.request.user.id,
            file_name=hashed_file_name,
        )

        try:
            presigned_url = s3_service.generate_presigned_upload_url(object_name=file_path)
            if not presigned_url:
                raise ValueError(_("Something went wrong while preparing your file upload. Please try again."))
        except Exception as e:
            logger.error(f"File upload error for path {file_path}: {str(e)}", exc_info=True)
            raise FileUploadError()

        # Save file metadata in DB
        serializer.validated_data["s3_key"] = file_path
        self.perform_create(serializer)

        return Response(
            {"presigned-url": presigned_url, **serializer.data},
            status=status.HTTP_201_CREATED
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
            {"message": _("File successfully updated.")},
            status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete the file by setting 'deleted_at' instead of deleting it."""
        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])
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
