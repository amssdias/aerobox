from rest_framework.routers import DefaultRouter

from apps.cloud_storage.views import CloudStorageViewSet
from apps.cloud_storage.views.folder import FolderViewSet
from apps.cloud_storage.views.share_link import ShareLinkViewSet

router = DefaultRouter()
router.register(r"folders", FolderViewSet, basename='folders')
router.register(r"share-links", ShareLinkViewSet, basename='share-links')
router.register(r"", CloudStorageViewSet, basename='storage')

urlpatterns = router.urls
