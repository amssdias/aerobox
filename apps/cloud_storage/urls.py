from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.cloud_storage.views import CloudStorageViewSet
from apps.cloud_storage.views.folder import FolderViewSet
from apps.cloud_storage.views.public_share import (
    PublicShareLinkDetail,
    PublicShareLinkFileDownloadView,
    PublicShareLinkAuthView,
)
from apps.cloud_storage.views.share_link import ShareLinkViewSet

urlpatterns = [
    path(
        "share/<str:token>/",
        PublicShareLinkDetail.as_view(),
        name="public-share-link-detail",
    ),
    path(
        "share/<str:token>/auth/",
        PublicShareLinkAuthView.as_view(),
        name="public-share-link-auth",
    ),
    path(
        "share/<str:token>/files/<int:file_id>/download/",
        PublicShareLinkFileDownloadView.as_view(),
        name="public-share-file-download",
    ),
]

router = DefaultRouter()
router.register(r"folders", FolderViewSet, basename="folders")
router.register(r"share-links", ShareLinkViewSet, basename="share-links")
router.register(r"", CloudStorageViewSet, basename="storage")

urlpatterns += router.urls
