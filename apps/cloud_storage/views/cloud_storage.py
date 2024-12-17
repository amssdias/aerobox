from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cloud_storage.models import CloudFile
from apps.cloud_storage.serializers import CloudFilesSerializer
from apps.cloud_storage.services import S3Service


class CloudStorageViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CloudFilesSerializer
    queryset = CloudFile.objects.all()

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)
        return queryset

    def list(self, request):
        return super(CloudStorageViewSet, self).list(request)

    @action(methods=["POST"], detail=False, url_path="get_s3_presigned_url", url_name="get_s3_presigned_url")
    def get_s3_presigned_url_to_upload(self, request):
        s3_service = S3Service()
        file_name = self.request.POST.get("file_name")
        object_name = f"users/{self.request.user.id}/{file_name}"
        presigned_url = s3_service.generate_presigned_upload_url(
            object_name=object_name
        )

        return Response(data="Nothing heereee", status=status.HTTP_200_OK)