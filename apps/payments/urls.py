from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.payments.views.checkout import CheckoutSessionViewSet

router = DefaultRouter()
router.register(r"checkout", CheckoutSessionViewSet, basename="checkout")

urlpatterns = [
    path("", include(router.urls)),
]
