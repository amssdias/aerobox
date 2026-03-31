from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.payments.api.views import CheckoutSessionViewSet

app_name = "payments"

router = DefaultRouter()
router.register(r"checkout", CheckoutSessionViewSet, basename="checkout")

urlpatterns = [
    path("", include(router.urls)),
]
