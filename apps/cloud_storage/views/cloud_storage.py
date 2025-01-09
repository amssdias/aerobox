from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.cloud_storage.serializers.cloud_files import CloudFileUpdateSerializer
from apps.cloud_storage.services import S3Service
from config.api_docs.openapi_schemas import RESPONSE_SCHEMA_GET_PRESIGNED_URL


@extend_schema_view(
    list=extend_schema(exclude=True),
    create=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True),
)
@extend_schema(tags=["API - Cloud Storage"])
class CloudStorageViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CloudFilesSerializer
    queryset = CloudFile.objects.all()

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "partial_update":
            return CloudFileUpdateSerializer
        return CloudFilesSerializer

    def list(self, request):
        return super(CloudStorageViewSet, self).list(request)

    def get_serializer_context(self):
        context = super().get_serializer_context()

        # Differentiate list vs. detail views
        context["is_detail"] = self.action == "retrieve"
        return context

    @extend_schema(responses={200: RESPONSE_SCHEMA_GET_PRESIGNED_URL})
    @action(methods=["POST"], detail=False, url_path="get_s3_presigned_url", url_name="get_s3_presigned_url")
    def get_s3_presigned_url_to_upload(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(data=serializer.errors, status=HTTP_400_BAD_REQUEST)

        s3_service = S3Service()

        file_path = serializer.validated_data.get("path")
        presigned_url = s3_service.generate_presigned_upload_url(
            object_name=file_path
        )

        serializer.save()
        return Response(data={"presigned-url": presigned_url, **serializer.data}, status=status.HTTP_200_OK)
