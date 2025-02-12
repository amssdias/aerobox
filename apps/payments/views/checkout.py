from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from apps.subscriptions.serializers.subscription import CheckoutSubscriptionSerializer


@extend_schema(tags=["API - Payments"])
class CheckoutSessionViewSet(viewsets.GenericViewSet):
    serializer_class = CheckoutSubscriptionSerializer

    @action(detail=False, methods=["post"], url_path="session")
    def create_checkout(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.get_checkout_session_url(user=request.user)
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
