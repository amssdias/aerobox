from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from apps.subscriptions.models import Plan
from apps.subscriptions.serializers.plan import PlanSerializer


@extend_schema(tags=["API - Subscriptions"])
class PlanListAPIView(ListAPIView):
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    pagination_class = None
