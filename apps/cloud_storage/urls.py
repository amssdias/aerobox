from rest_framework.routers import DefaultRouter
from apps.cloud_storage.views import CloudStorageViewSet

router = DefaultRouter()
router.register(r"", CloudStorageViewSet, basename='storage')

urlpatterns = router.urls
