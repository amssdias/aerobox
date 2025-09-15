from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.subscriptions.views.plan import PlanListAPIView
from apps.subscriptions.views.subscription import SubscriptionViewSet
from apps.subscriptions.views.user_subscription import UserSubscriptionView

router = DefaultRouter()
router.register(r"", SubscriptionViewSet, basename="subscriptions")

urlpatterns = [
    path("plans/", PlanListAPIView.as_view(), name="plan-list"),
    path(
        "user-subscription/", UserSubscriptionView.as_view(), name="user-subscription"
    ),
    path("", include(router.urls)),
]
