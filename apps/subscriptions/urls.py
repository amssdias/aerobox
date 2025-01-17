from django.urls import path

from apps.subscriptions.views.plan import PlanListAPIView

urlpatterns = [
    path("plans/", PlanListAPIView.as_view(), name="plan-list"),
]
