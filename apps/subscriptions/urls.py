from django.urls import path

from apps.subscriptions.views.plan import PlanListAPIView
from apps.subscriptions.views.user_subscription import UserSubscriptionView


urlpatterns = [
    path("plans/", PlanListAPIView.as_view(), name="plan-list"),
    path("user-subscription/", UserSubscriptionView.as_view(), name="user-subscription"),
]
